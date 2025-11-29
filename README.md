# TriPhotos - Organisation Automatique de Photos

Script Python pour organiser automatiquement vos photos par date et lieu.

## Description

Ce script analyse les photos de votre smartphone et les organise dans des dossiers structurés selon le format `[AAAA-MM-JJ] - [Ville]`.

### Fonctionnalités

- **Extraction de la date** :
  - Priorité 1 : Données EXIF (DateTimeOriginal, DateTime, DateTimeDigitized)
  - Priorité 2 : Timestamp dans le nom du fichier
  - Fallback : Date de modification du fichier

- **Géolocalisation** :
  - Extraction des coordonnées GPS depuis les métadonnées EXIF
  - Géocodage inverse avec Nominatim (OpenStreetMap) pour obtenir le nom de la ville
  - Photos sans GPS : placées dans un dossier `[Date] - Inconnu`

- **Gestion intelligente** :
  - Renommage automatique en cas de fichiers en double
  - Support de multiples formats d'image (JPG, PNG, HEIC, RAW, etc.)
  - Déplacement sécurisé des fichiers

## Prérequis

- Python 3.7 ou supérieur
- Connexion internet (pour le géocodage avec Nominatim)

## Installation

1. Clonez ou téléchargez ce projet

2. Installez les dépendances :
```bash
pip install -r requirements.txt
```

Les bibliothèques nécessaires sont :
- `Pillow` : Lecture des métadonnées EXIF des images
- `geopy` : Géocodage inverse pour obtenir les noms de villes

## Configuration

Aucune configuration n'est nécessaire ! Le script peut être utilisé directement.

Le dossier **Destination** est créé automatiquement au même niveau que le dossier source.

## Utilisation

### Utilisation Basique

**Option 1 : Répertoire courant (par défaut)**

Placez-vous dans le dossier contenant vos photos et exécutez :
```bash
python organize_photos.py
```

**Option 2 : Spécifier un répertoire**

Vous pouvez indiquer le chemin du dossier contenant les photos :
```bash
# Chemin relatif
python organize_photos.py ./mes_photos

# Chemin absolu
python organize_photos.py C:\Photos\Vacances
```

### Afficher l'aide

Pour voir toutes les options disponibles :
```bash
python organize_photos.py --help
```

### Ce que fait le script

Le script va :
   - Analyser chaque photo du dossier source
   - Extraire la date et les coordonnées GPS
   - Interroger Nominatim pour obtenir la ville
   - Créer les sous-dossiers nécessaires dans **Destination**
   - Déplacer les photos (elles seront retirées du dossier Source)

## Exemple de Résultat

```
Destination/
├── 2024-12-24 - Gazeran/
│   ├── IMG_001.jpg
│   └── IMG_002.jpg
├── 2024-12-25 - Bailly/
│   ├── IMG_003.jpg
│   └── IMG_004.jpg
├── 2024-12-25 - Noisy le Roi/
│   └── IMG_005.jpg
└── 2024-12-26 - Inconnu/
    └── IMG_006.jpg  (photo sans GPS)
```

## Formats Supportés

Le script traite les fichiers avec les extensions suivantes :
- `.jpg`, `.jpeg`
- `.png`
- `.heic`, `.heif`
- `.raw`, `.cr2`, `.nef`, `.arw`

## Limitation de Nominatim

Le script respecte la politique d'utilisation de Nominatim :
- Maximum 1 requête par seconde
- Le traitement peut donc prendre du temps pour un grand nombre de photos

## Logs et Suivi

Le script affiche en temps réel :
- Le nom de chaque photo traitée
- La date extraite
- Les coordonnées GPS (si disponibles)
- La ville identifiée
- Le dossier de destination

Exemple de sortie :
```
📸 Traitement: IMG_20241224_153022.jpg
  📅 Date: 2024-12-24
  📍 GPS: 48.756080, 1.982450
  🏙 Ville: Gazeran
  ✅ Déplacé vers: 2024-12-24 - Gazeran/IMG_20241224_153022.jpg
```

## Résolution de Problèmes

### Les photos ne sont pas détectées
- Vérifiez que les extensions de fichiers sont bien supportées
- Assurez-vous que les fichiers sont directement dans le dossier Source (pas dans des sous-dossiers)

### Erreur de géocodage
- Vérifiez votre connexion internet
- Nominatim peut parfois être lent ou indisponible, réessayez plus tard

### Photos marquées comme "Inconnu"
- Les photos n'ont pas de métadonnées GPS
- Vérifiez que la localisation était activée sur votre smartphone lors de la prise de vue

## Support

Pour toute question ou problème, consultez les logs d'exécution du script qui détaillent chaque étape du traitement.

## Avertissement

Ce script **déplace** les photos du dossier Source vers Destination. Assurez-vous d'avoir une sauvegarde de vos photos avant la première utilisation, ou testez d'abord avec quelques photos.
