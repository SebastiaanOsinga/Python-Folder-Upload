import os
import sys
import subprocess
import uuid
import shutil
from pathlib import Path
from config import nyuu_config

# Instellingen
media_exts = ['.mkv', '.mp4', '.mp3', '.flac', '.avi', '.mov'] # Voeg extentie toe die geupload moeten worden naar used
tmp_dir = Path.home() / 'tmp'
nzb_output_dir = Path.home() / 'nzb_dump'
tmp_dir.mkdir(parents=True, exist_ok=True)
nzb_output_dir.mkdir(parents=True, exist_ok=True)

def scan_media_files(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if Path(f).suffix.lower() in media_exts:
                files.append(Path(root) / f)
    return files

def rar_file(source_file, unique_basename):
    rar_path = tmp_dir / f"{unique_basename}.rar"
    if rar_path.exists():
        print(f'RAR-bestand bestaat al: {rar_path}')
        return rar_path

    # RAR-bestand splitsen in 250MB (250m)
    cmd = [
        'rar', 'a',
        '-m0',                          # Geen compressie
        '-ep1',               # <--- Voorkom opslaan van pad
        f"-v250m",                      # Split in volumes van 250MB
        str(tmp_dir / unique_basename),# Basisnaam zonder extensie
        str(source_file)
    ]
    subprocess.run(cmd, check=True)
    return tmp_dir / f"{unique_basename}.part1.rar"

def create_par2(unique_basename):
    # Maak PAR2 over alle bijbehorende RAR-bestanden
    files = list(tmp_dir.glob(f"{unique_basename}*.rar"))
    if not files:
        raise FileNotFoundError("Geen .rar bestanden gevonden voor par2.")

    cmd = ['par2', 'create', '-r5', str(tmp_dir / f"{unique_basename}"), *[str(f) for f in files]]
    subprocess.run(cmd, check=True)

def upload_nyuu(unique_basename, nzb_name):
    rar_parts = list(tmp_dir.glob(f"{unique_basename}*.rar"))
    par2_files = list(tmp_dir.glob(f"{unique_basename}*.par2"))

    files_to_upload = [str(f) for f in rar_parts + par2_files]

    nzb_path = nzb_output_dir / nzb_name

    cmd = [
        'nyuu',
        '-n', str(nyuu_config['connections']),
        '-g', nyuu_config['newsgroup'],
        *files_to_upload,
        '-S',
        '-h', nyuu_config['host'],
        '-P', str(nyuu_config['port']),
        '-u', nyuu_config['username'],
        '-p', nyuu_config['password'],
        '-f', nyuu_config['from'],
        '-o', str(nzb_path)
    ]
    subprocess.run(cmd, check=True)

    print(f'>> NZB opgeslagen als: {nzb_path}')
    return True

def clean_tmp_files(unique_basename):
    for f in tmp_dir.glob(f"{unique_basename}*"):
        f.unlink()
    print(f'>> Tijdelijke bestanden verwijderd voor: {unique_basename}')

def process_file(file_path):
    print(f'\n>> Verwerken: {file_path.name}')
    unique_basename = uuid.uuid4().hex  # Zonder streepjes
    try:
        rar_file(file_path, unique_basename)
        create_par2(unique_basename)
        nzb_name = file_path.with_suffix('.nzb').name
        upload_nyuu(unique_basename, nzb_name)
        clean_tmp_files(unique_basename)
    except subprocess.CalledProcessError as e:
        print(f'FOUT tijdens verwerken: {file_path.name}: {e}')
    except Exception as ex:
        print(f'Algemene fout: {ex}')

def main():
    if len(sys.argv) != 2:
        print(f'Gebruik: python3 {sys.argv[0]} /pad/naar/mediafolder')
        return

    media_dir = Path(sys.argv[1])
    if not media_dir.is_dir():
        print('Ongeldige folder opgegeven.')
        return

    files = scan_media_files(media_dir)
    if not files:
        print('Geen mediabestanden gevonden.')
        return

    for f in files:
        process_file(f)

if __name__ == '__main__':
    main()

