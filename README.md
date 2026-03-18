# Covid_pipi
Surveillance du COVID dans les eaux usées à Besançon

Script python visant à télécharger les données de COVID dans les eaux usées et à les comparer avec les données nationales

Installation
1. Installer Python
2.  Installer Doker
3. Placer les fichier dockerfile et script.py dans un même répertoire (ici sur le bureau)

Construction et lancement du Docker : 
- cd Bureau/covid_pipi_docker
- docker build -t covid_pipi_docker .
- docker run --rm -v "$PWD:/app" covid_pipi_docker
----
  - Source des données : https://odisse.santepubliquefrance.fr/explore/dataset/sum-eau-indicateurs/information/
  - Prévisualisation du résultat : https://drive.proton.me/urls/5AVHE7P2GG#Hbyp0kdUeqSF
