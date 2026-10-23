<?php
// Synthetic integration database only; no production services are accessed.
$pdo = new PDO('sqlite:/var/www/storage/database/dreeve.db');
echo json_encode([
    'activities' => $pdo->query('SELECT * FROM Activity ORDER BY startDateTime')->fetchAll(PDO::FETCH_ASSOC),
    'imports' => $pdo->query('SELECT originalFilename,status,errorMessage FROM FileImport')->fetchAll(PDO::FETCH_ASSOC),
], JSON_THROW_ON_ERROR);
