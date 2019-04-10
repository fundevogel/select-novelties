<?php

require_once('vendor/autoload.php');

$currentIssue = '2019_01';


function generateIssue($issue)
{
    $object = new PCBIS2PDF\PCBIS2PDF('dist/' . $issue . '/images');

    $src      = './src/' . $issue;
    $dist     = './dist/' . $issue;

    foreach (glob($src . '/csv/*.csv') as $file) {
        $fromCSV = $object->CSV2PHP($file);
        $data = $object->process($fromCSV);
        $object->PHP2CSV($data, $dist . '/csv/' . basename($file));
    }

    /**************************************************************************/

    $dataFile = $dist . '/data.csv';
    $object->mergeCSV(glob($dist . '/csv/*.csv'), $dataFile, true);

    /**************************************************************************/

    $template = $src . '/templates/dataList.sla';

    if (file_exists($template)) {
        $command = [
            './vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py', // Python script
            '--single', // Single file output
            '-c ' . $dataFile, // CSV file
            '-d ";"', // Semicolon as delimiter
            '-o ' . $dist . '/templates', // Output path
            '-n ' . basename($template, '.sla'), // Output filename (without extension)
            $template, // Template path
        ];

        exec(implode(' ', $command), $result);
        a::show($result);
    }

    return;
}

generateIssue($currentIssue);
