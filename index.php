<?php

require_once('vendor/autoload.php');

$currentIssue = '2019_01';


function generateIssue($issue)
{
    $src = './src/' . $issue;
    $dist = './dist/' . $issue;


    /**
     * Processing `.csv` source files
     *
     * `src/ISSUE/csv/example.csv` >> `dist/ISSUE/csv/example.csv`
     *
     */

    $object = new PCBIS2PDF\PCBIS2PDF;
    $object->setImagePath($dist . '/images');
    $object->setCachePath($dist . '/.cache');

    foreach (glob($src . '/csv/*.csv') as $dataFile) {
        $fromCSV = $object->CSV2PHP($dataFile, ';');
        $data = $object->processData($fromCSV);
        $object->PHP2CSV($data, $dist . '/csv/' . basename($dataFile));
    }

    /**************************************************************************/

    /**
     * Processing `.sla` source files (with corresponding `.csv` files)
     *
     * `src/ISSUE/templates/example.sla` >> `dist/ISSUE/templates/example.sla`
     * using `dist/ISSUE/csv/example.csv` + `src/ISSUE/csv/dataList.csv` as backup
     *
     */

    foreach (glob($dist . '/csv/*.csv') as $dataFile) {
        $templateFile = $src . '/templates/' . basename($dataFile, 'csv') . 'sla';

        if (!file_exists($templateFile)) {
            $templateFile = $src . '/templates/dataList.sla';
        }

        if (file_exists($dist . '/templates/' . basename($dataFile, 'csv') . 'sla')) {
            continue;
        }

        $command = [
            './vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py', // Python script
            '--single', // Single file output
            '-c ' . $dataFile, // CSV file
            '-o ' . $dist . '/templates', // Output path
            '-n ' . basename($dataFile, '.csv'), // Output filename (without extension)
            $templateFile, // Template path
        ];

        exec(implode(' ', $command), $result);
        a::show($result);
    }

    /**************************************************************************/

    /**
     * Creating `.pdf` files from `.sla` destination files
     *
     * `dist/ISSUE/templates/example.sla` >> `dist/ISSUE/documents/raw/example.pdf`
     *
     */

    foreach (glob($dist . '/templates/*.sla') as $templateFile) {
        $command = [
            // or simply `scribus` if installed via package manager
            'flatpak run net.scribus.Scribus',
            '-g',
            '-py ./scripts/to-pdf.py',
            '--',
            $templateFile,
        ];

        exec(implode(' ', $command), $result);
        a::show($result);
    }

    foreach (glob($dist . '/templates/*.pdf') as $pdfFile) {
        rename($pdfFile, $dist . '/documents/raw/' . basename($pdfFile));
    }

    /**************************************************************************/

    /**
     * Optimizing `.pdf` files with Ghostscript
     *
     * `dist/ISSUE/documents/raw/example.pdf` >> `dist/ISSUE/documents/optimized/example.pdf`
     *
     */

    foreach (glob($dist . '/documents/raw/*.pdf') as $pdfFile) {
        $outputFile = dirname($pdfFile, 2) . '/optimized/' . basename($pdfFile);

        $command = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dConvertCMYKImagesToRGB=true',
            '-dSubsetFonts=true',
            '-dCompressFonts=true',
            '-dPDFSETTINGS=/printer',
            '-dDownsampleColorImages=true',
            '-dDownsampleGrayImages=true',
            '-dDownsampleMonoImages=true',
            '-dColorImageResolution=250',
            '-dGrayImageResolution=250',
            '-dMonoImageResolution=250',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            '-sOutputFile=' . $outputFile,
            '-c .setpdfwrite',
            '-f ' . $pdfFile,
        ];

        exec(implode(' ', $command), $result);
        a::show($result);
    }

    /**************************************************************************/

    /**
     * Merging optimized `.pdf` files with Poppler (see https://poppler.freedesktop.org)
     *
     * `dist/ISSUE/documents/optimized/example.pdf` >> `dist/ISSUE/example.pdf`
     *
     */

    $pdfFiles = glob($dist . '/documents/optimized/*.pdf');
    $outputFile = $dist . '/issue_' . $issue . '.pdf';

    $command = [
        'pdfunite',
        implode(' ', $pdfFiles),
        $outputFile
    ];

    exec(implode(' ', $command), $result);
    a::show($result);

    return;
}

generateIssue($currentIssue);
