# MediaShow Photo

MediaShow Photo est une application de diaporama légère et intuitive, conçue pour organiser, trier et présenter vos photos simplement.

## Fonctionnalités principales

* **Chargement flexible** : Importez des photos individuellement ou chargez des dossiers complets.
* **Organisation dynamique** : Triez vos photos par nom, par date (création ou modification) ou de manière aléatoire.
* **Gestion de liste** : Visualisez vos photos avec des miniatures, sélectionnez-les pour les supprimer de votre liste de lecture ou prévisualisez-les en grand avant le lancement.
* **Diaporama interactif** : Lancez vos présentations en plein écran avec une minuterie réglable.
    * *Contrôles au clavier* :
        * `Espace` : Pause / Lecture.
        * `Flèches Gauche/Droite` : Navigation manuelle entre les photos.
        * `Échap` : Quitter le diaporama.
* **Playlists** : Sauvegardez vos sélections préférées dans des fichiers de playlist (`.txt`) pour les retrouver plus tard.
* **Robustesse** : L'application vérifie la validité des images et gère automatiquement les erreurs de lecture pour éviter tout plantage.

## Installation et Utilisation

1. Assurez-vous d'avoir Python et la bibliothèque `PySide6` installés.
2. Placez le fichier `main.py` dans le dossier `~/Desktop/MonMediaShow/`.
3. Lancez l'application via le terminal ou votre script de lancement `.command`.

## Structure du projet

* `main.py` : Le cœur de l'application (interface et logique).
* `playlists/` : Dossier contenant vos fichiers de sauvegarde de playlists.

## Objectif du projet
Cette application a été créée pour offrir une solution stable, rapide et facile à maintenir pour la gestion quotidienne de photos, en privilégiant l'expérience utilisateur et la fiabilité.
