#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour organiser automatiquement les photos par date et lieu.
Les photos sont classées dans des dossiers nommés "[AAAA-MM-JJ] - [Ville]"
"""

import os
import sys
import re
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import time

# Configuration de l'encodage pour Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


class PhotoOrganizer:
    """Classe pour organiser les photos par date et lieu"""

    def __init__(self, source_dir: str, destination_dir: str):
        self.source_dir = Path(source_dir)
        self.destination_dir = Path(destination_dir)
        self.geolocator = Nominatim(user_agent="photo_organizer_v1.0")
        self.processed_count = 0
        self.error_count = 0
        self.photo_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw'}

    def get_exif_data(self, image_path: Path) -> dict:
        """Extrait les données EXIF d'une image"""
        try:
            image = Image.open(image_path)
            exif_data = {}

            if hasattr(image, '_getexif') and image._getexif() is not None:
                exif = image._getexif()
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = value

            return exif_data
        except Exception as e:
            print(f"  ⚠ Erreur lecture EXIF pour {image_path.name}: {e}")
            return {}

    def get_gps_coordinates(self, exif_data: dict) -> Optional[Tuple[float, float]]:
        """Extrait les coordonnées GPS des données EXIF"""
        try:
            gps_info = exif_data.get('GPSInfo')
            if not gps_info:
                return None

            gps_data = {}
            for key in gps_info.keys():
                decode = GPSTAGS.get(key, key)
                gps_data[decode] = gps_info[key]

            if 'GPSLatitude' not in gps_data or 'GPSLongitude' not in gps_data:
                return None

            # Conversion des coordonnées
            lat = self._convert_to_degrees(gps_data['GPSLatitude'])
            lon = self._convert_to_degrees(gps_data['GPSLongitude'])

            # Gestion des références (N/S, E/W)
            if gps_data.get('GPSLatitudeRef') == 'S':
                lat = -lat
            if gps_data.get('GPSLongitudeRef') == 'W':
                lon = -lon

            return (lat, lon)
        except Exception as e:
            print(f"  ⚠ Erreur extraction GPS: {e}")
            return None

    def _convert_to_degrees(self, value) -> float:
        """Convertit les coordonnées GPS en degrés décimaux"""
        d, m, s = value
        return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)

    def get_city_from_coordinates(self, lat: float, lon: float) -> str:
        """Obtient le nom de la ville à partir des coordonnées GPS via Nominatim"""
        try:
            # Respect de la politique d'usage de Nominatim (max 1 requête/seconde)
            time.sleep(1)

            location = self.geolocator.reverse(f"{lat}, {lon}", language='fr', timeout=10)

            if location and location.raw.get('address'):
                address = location.raw['address']
                # Priorité: village, town, city, municipality
                city = (address.get('village') or
                       address.get('town') or
                       address.get('city') or
                       address.get('municipality') or
                       address.get('county', 'Inconnu'))
                return city
            return 'Inconnu'
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"  ⚠ Erreur géocodage: {e}")
            return 'Inconnu'
        except Exception as e:
            print(f"  ⚠ Erreur inattendue géocodage: {e}")
            return 'Inconnu'

    def get_date_from_exif(self, exif_data: dict) -> Optional[datetime]:
        """Extrait la date de prise de vue des données EXIF"""
        date_tags = ['DateTimeOriginal', 'DateTime', 'DateTimeDigitized']

        for tag in date_tags:
            if tag in exif_data:
                try:
                    date_str = exif_data[tag]
                    # Format EXIF: "YYYY:MM:DD HH:MM:SS"
                    return datetime.strptime(str(date_str), '%Y:%m:%d %H:%M:%S')
                except Exception as e:
                    print(f"  ⚠ Erreur parsing date EXIF {tag}: {e}")
                    continue
        return None

    def get_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extrait la date du nom de fichier (plusieurs formats possibles)"""
        # Format: YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD, IMG_YYYYMMDD, etc.
        patterns = [
            r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})',  # YYYYMMDD, YYYY-MM-DD, YYYY_MM_DD
            r'(\d{8})',  # YYYYMMDD continu
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                    else:
                        date_str = match.group(1)
                        year = date_str[:4]
                        month = date_str[4:6]
                        day = date_str[6:8]

                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue
        return None

    def get_photo_date(self, image_path: Path, exif_data: dict) -> Optional[datetime]:
        """Obtient la date de la photo (priorité EXIF, puis nom de fichier)"""
        # Priorité 1: EXIF
        date = self.get_date_from_exif(exif_data)
        if date:
            return date

        # Priorité 2: Nom de fichier
        date = self.get_date_from_filename(image_path.name)
        if date:
            return date

        # Fallback: date de modification du fichier
        timestamp = image_path.stat().st_mtime
        return datetime.fromtimestamp(timestamp)

    def get_unique_filename(self, destination_path: Path) -> Path:
        """Génère un nom de fichier unique en ajoutant un suffixe si nécessaire"""
        if not destination_path.exists():
            return destination_path

        # Ajouter un suffixe numérique
        counter = 1
        stem = destination_path.stem
        suffix = destination_path.suffix
        parent = destination_path.parent

        while destination_path.exists():
            new_name = f"{stem}_{counter}{suffix}"
            destination_path = parent / new_name
            counter += 1

        return destination_path

    def process_photo(self, image_path: Path):
        """Traite une photo individuelle"""
        print(f"\n📸 Traitement: {image_path.name}")

        try:
            # Lecture des données EXIF
            exif_data = self.get_exif_data(image_path)

            # Extraction de la date
            photo_date = self.get_photo_date(image_path, exif_data)
            date_str = photo_date.strftime('%Y-%m-%d')
            print(f"  📅 Date: {date_str}")

            # Extraction des coordonnées GPS et de la ville
            coordinates = self.get_gps_coordinates(exif_data)
            if coordinates:
                lat, lon = coordinates
                print(f"  📍 GPS: {lat:.6f}, {lon:.6f}")
                city = self.get_city_from_coordinates(lat, lon)
            else:
                print(f"  ⚠ Pas de coordonnées GPS")
                city = 'Inconnu'

            print(f"  🏙 Ville: {city}")

            # Création du nom du dossier de destination
            folder_name = f"{date_str} - {city}"
            destination_folder = self.destination_dir / folder_name
            destination_folder.mkdir(parents=True, exist_ok=True)

            # Déplacement du fichier
            destination_path = destination_folder / image_path.name
            destination_path = self.get_unique_filename(destination_path)

            shutil.move(str(image_path), str(destination_path))
            print(f"  ✅ Déplacé vers: {destination_folder.name}/{destination_path.name}")

            self.processed_count += 1

        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            self.error_count += 1

    def organize_photos(self):
        """Organise toutes les photos du dossier source"""
        print(f"\n{'='*60}")
        print(f"🚀 Démarrage de l'organisation des photos")
        print(f"{'='*60}")
        print(f"📂 Source: {self.source_dir}")
        print(f"📂 Destination: {self.destination_dir}")

        # Vérification des dossiers
        if not self.source_dir.exists():
            print(f"\n❌ Le dossier source n'existe pas: {self.source_dir}")
            return

        self.destination_dir.mkdir(parents=True, exist_ok=True)

        # Parcours des fichiers
        photo_files = [
            f for f in self.source_dir.iterdir()
            if f.is_file() and f.suffix.lower() in self.photo_extensions
        ]

        if not photo_files:
            print(f"\n⚠ Aucune photo trouvée dans {self.source_dir}")
            return

        print(f"\n📊 {len(photo_files)} photo(s) trouvée(s)")

        for photo_file in photo_files:
            self.process_photo(photo_file)

        # Résumé
        print(f"\n{'='*60}")
        print(f"✅ Traitement terminé!")
        print(f"{'='*60}")
        print(f"📊 Photos traitées: {self.processed_count}")
        print(f"❌ Erreurs: {self.error_count}")
        print(f"{'='*60}\n")


def main():
    """Fonction principale"""
    # Configuration des arguments de ligne de commande
    parser = argparse.ArgumentParser(
        description="Organise automatiquement les photos par date et lieu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python organize_photos.py                    # Utilise le répertoire courant
  python organize_photos.py ./mes_photos       # Utilise le répertoire spécifié
  python organize_photos.py C:\\Photos\\Vacances  # Utilise un chemin absolu
        """
    )
    parser.add_argument(
        'source_dir',
        nargs='?',
        default='.',
        help='Répertoire contenant les photos à organiser (par défaut: répertoire courant)'
    )

    args = parser.parse_args()

    # Configuration du dossier source
    source_path = Path(args.source_dir).resolve()

    # Le dossier Destination est créé automatiquement au même niveau que Source
    parent_dir = source_path.parent
    DESTINATION_DIR = parent_dir / "Destination"

    print(f"Configuration:")
    print(f"  Source: {source_path}")
    print(f"  Destination: {DESTINATION_DIR}")
    print()

    # Création de l'organisateur et lancement
    organizer = PhotoOrganizer(str(source_path), str(DESTINATION_DIR))
    organizer.organize_photos()


if __name__ == "__main__":
    main()
