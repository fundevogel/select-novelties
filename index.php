<?php

require_once('vendor/autoload.php');

function csv($issue = '2019_01')
{
    $object = new PCBIS2PDF\PCBIS2PDF;
    $csv_raw = glob('./src/' . $issue . '/csv_raw/*.csv');

    foreach ($csv_raw as $file) {
        $fromCSV = $object->CSV2PHP($file);
        $arrayFile = $object->process($fromCSV);

        $outputData = [];

        foreach ($arrayFile as $array) {
            $category = basename($file, '.csv');
            $array = a::update($array, ['Kategorie' => $category]);

            $outputData[] = $array;
        }

        $object->PHP2CSV($outputData, './src/' . $issue . '/csv_done/' . basename($file));
    }
    return;
}

csv();

function scribus($issue = '2019_01')
{
    $files = glob('./src/' . $issue . '/csv_done/*.csv');

    foreach ($files as $file) {
        $template = './src/'. $issue . '/templates/' . basename($file, '.csv') . '.sla';

        if (file_exists($template)) {
            $command = [
                './vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py', // Python script
                '--single', // Single file output
                '-c ' . $file, // CSV file
                '-d ";"', // Semicolon as delimiter
                '-o dist/' . $issue . '/partials', // Output path
                '-n ' . basename($file, '.csv'), // Output filename (without extension)
                $template, // Template path
            ];

            exec(implode(' ', $command), $result);
            print_r($result);
        }
    }
    return;
}

scribus();
