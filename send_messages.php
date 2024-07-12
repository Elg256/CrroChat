<?php
// Récupérer le contenu à ajouter du corps de la requête POST
$contenu = $_POST['contenu'];
$file_name = $_POST["file_name"];


// Chemin vers le fichier texte
$fichier = $file_name;

// Ouvrir le fichier en mode ajout
$handle = fopen($fichier, 'a');

// Ajouter le contenu au fichier
fwrite($handle, $contenu);

// Fermer le fichier
fclose($handle);
?>
