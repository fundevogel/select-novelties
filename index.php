#!/usr/bin/env php

<?php

/*
 * INCLUDES
 */

require_once('vendor/autoload.php');


/*
 * VARIABLES
 */

$issue = isset($argv[1]) ? $argv[1] : die('I find your lack of arguments disturbing.' . "\n");


$src  = realpath('./issues/' . $issue . '/src');
$dist = realpath('./issues/' . $issue . '/dist');
$shared = realpath('./shared');

$season = substr($issue, -2) == "01"
    ? "spring"
    : "autumn"
;

$general = [
    'hoerbuch' => 15,
    'besonderes' => 14,
    'sachbuch' => 13,
    'ab14' => 12,
    'ab12' => 11,
    'ab10' => 10,
    'ab8' => 9,
    'ab6' => 8,
    'vorlesebuch' => 7,
    'bilderbuch' => 6,
    'toddler' => 5,
];

$specials = $season === 'spring'
    ? [
        'ostern' => 16,
    ]
    : [
        'kalender' => 17,
        'weihnachten' => 16,
    ]
;

$categories = array_merge($specials, $general);


/*
 * FUNCTIONS
 */

function makePDF(string $scribusFile, string $documentFile = '')
{
    if (!$scribusFile || !file_exists($scribusFile)) {
        exit('Please provide a valid SLA file!' . "\n");
    }

    $command = [
        'flatpak run net.scribus.Scribus -g -py ./scripts/pdf-gen.py', // Python script
        '--input ' . $scribusFile,
        '--output ' . $documentFile
    ];

    exec(implode(' ', $command), $result);
    print_r($result);
}


/*
 * MAIN
 */

if (!isset($argv[2])) {

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
     * Using `ISSUE/dist/csv/example.csv` with either
     *
     * a) `ISSUE/src/templates/example.sla`,
     * b) `ISSUE/src/templates/dataList.sla` or
     * c) `shared/templates/dataList.sla` as fallback
     *
     * >> `ISSUE/dist/templates/example.sla`
     *
     */

    foreach (glob($dist . '/csv/*.csv') as $dataFile) {
        $templateName = basename($dataFile, 'csv') . 'sla';
        $templateFile = $src . '/templates/' . $templateName;

        // Check if per-issue template file for given category exists
        if (!file_exists($templateFile)) {
            // If it doesn't, choose per-issue generic template file
            $templateFile = $src . '/templates/dataList.sla';

            if (!file_exists($templateFile)) {
                // If that doesn't exist either, choose common template file
                $templateFile = $shared . '/templates/dataList.sla';
            }
        }

        $command = [
            './vendor/berteh/scribusgenerator/ScribusGeneratorCLI.py', // Python script
            '--single', // Single file output
            '-c ' . $dataFile, // CSV file
            '-o ' . $dist . '/templates/partials', // Output path
            '-n ' . basename($dataFile, '.csv'), // Output filename (without extension)
            $templateFile, // Template path
        ];

        exec(implode(' ', $command), $result);
        print_r($result);
    }

    /**************************************************************************/

    /**
     * Importing `.sla` category partials into main `.sla` file
     *
     * `ISSUE/dist/templates/*.sla` >> `ISSUE/dist/processed.sla`
     *
     */

    $mainFile = $src . '/templates/main.sla';

    // Check if per-issue main file exists
    if (!file_exists($mainFile)) {
        // If it doesn't, choose common main file
        $mainFile = $shared . '/templates/' . $season . '.sla';
    }

    $baseFile = $dist . '/templates/unprocessed.sla';
    $processedFile = $dist . '/templates/processed.sla';

    copy($mainFile, $baseFile);

    $count = 0;

    foreach ($categories as $category => $page_number) {
        $categoryFile = $dist . '/templates/partials/' . $category . '.sla';

        if (!file_exists($categoryFile)) {
            print_r('File doesn\'t exist: ' . $categoryFile);
            continue;
        }

        if ($count > 0) {
            $baseFile = $processedFile;
        }

        $command = [
            'flatpak run net.scribus.Scribus -g -py ./scripts/sla-import.py', // Python script
            $baseFile, // Base file
            $categoryFile, // Import file
            '--page ' . $page_number,
            '--output ' . $processedFile,
            '--masterpage category_' . $season . '_' . $category,
        ];

        $count++;

        exec(implode(' ', $command), $result);
        print_r($result);
    }

    /**************************************************************************/

    /**
     * Replacing all instances of pattern %%YEAR%% with current year
     */

    $pattern = '%%YEAR%%';

    $command = [
        'python ./scripts/replace-year.py', // Python script
        $processedFile, // (processed) base file
        '--pattern ' . $pattern,
    ];

    exec(implode(' ', $command), $result);
    print_r($result);

    /**************************************************************************/

    /**
     * Generating `.pdf` file for review
     *
     * `ISSUE/dist/templates/processed.sla` >> `ISSUE/dist/documents/raw.pdf`
     */

    $documentFile = $dist . '/documents/raw.pdf';

    makePDF($processedFile, $documentFile);

    // This file will be edited
    copy($processedFile, $dist . '/templates/edited.sla');

} elseif (isset($argv[2]) && $argv[2] === '--build') {

    /**
     * Generating the final `.pdf` file after reviewing & editing by hand
     *
     * `ISSUE/dist/templates/edited.sla` >> `ISSUE/dist/documents/final.pdf`
     */

    $scribusFile = $dist . '/templates/edited.sla';
    $documentFile = $dist . '/documents/final.pdf';

    makePDF($scribusFile, $documentFile);

    /**
     * Optimizing `.pdf` files with Ghostscript
     *
     * `ISSUE/dist/documents/bloated.pdf` >> `ISSUE/dist/optimized.pdf`
     *
     */

    $imageResolution = '1';
    $seasonLocale = $season === 'spring'
        ? 'fruehjahr'
        : 'herbst'
    ;

    $outputName = date('Y') . '-' . $seasonLocale . '-buchempfehlungen.pdf';
    $outputFile = dirname($documentFile, 3) . '/' . $outputName;

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
        '-dColorImageResolution=' . $imageResolution,
        '-dGrayImageResolution=' . $imageResolution,
        '-dMonoImageResolution=' . $imageResolution,
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        '-sOutputFile=' . $outputFile,
        '-c .setpdfwrite',
        '-f ' . $documentFile,
    ];

    exec(implode(' ', $command), $result);
    print_r('Finished!');
} else {
    die('Please provide a valid issue identifier.' . "\n");
}
