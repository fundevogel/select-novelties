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
$debug = in_array('--debug', $argv);

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
        'flatpak run net.scribus.Scribus -g -py ./scripts/generate_pdf.py', // Python script
        '--input ' . $scribusFile,
        '--output ' . $documentFile
    ];

    exec(implode(' ', $command), $result);

    return $result;
}

function printResult(array $array = [])
{
    foreach ($array as $line) {
        echo $line . "\n";
    }
}


/*
 * MAIN
 */

if (!isset($argv[2]) || $argv[2] !== '--build') {

    /**
     * Checking for duplicate entries in `.csv` source files
     */

    echo('Checking for duplicate entries in `.csv` source files' . "\n");

    exec('bash scripts/find_duplicates.bash ' . $issue, $result);

    if (!empty($result)) {
        printResult($result);

        die('Resolve duplicates first!' . "\n");
    }

    /**************************************************************************/

    /**
     * Processing `.csv` source files
     *
     * `src/ISSUE/csv/example.csv` >> `dist/ISSUE/csv/example.csv`
     *
     */

    echo('Processing `.csv` source files' . "\n");

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

    echo('Processing `.sla` source files (with corresponding `.csv` files)' . "\n");

    foreach (glob($dist . '/csv/*.csv') as $dataFile) {
        $templateName = basename($dataFile, 'csv') . 'sla';
        $templateFile = $src . '/templates/' . $templateName;

        // Check if per-issue template file for given category exists ..
        if (!file_exists($templateFile)) {
            // .. if it doesn't, choose per-issue generic template file
            $templateFile = $src . '/templates/dataList.sla';
        }

        // Otherwise ..
        if (!file_exists($templateFile)) {
            // .. common template file for given category
            $templateFile = $shared . '/templates/partials/' . $templateName;
        }

        // But if that doesn't exist either ..
        if (!file_exists($templateFile)) {
            // .. ultimately resort to common generic template file
            $templateFile = $shared . '/templates/partials/dataList.sla';
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

        if ($debug && !empty($result)) {
            printResult($result);
        }
    }

    /**************************************************************************/

    /**
     * Importing `.sla` category partials into main `.sla` file
     *
     * `ISSUE/dist/templates/*.sla` >> `ISSUE/dist/processed.sla`
     *
     */

    echo('Importing `.sla` category partials into main `.sla` file' . "\n");

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
            echo('File doesn\'t exist: ' . $categoryFile . "\n");
            continue;
        }

        if ($count > 0) {
            $baseFile = $processedFile;
        }

        $command = [
            'flatpak run net.scribus.Scribus -g -py ./scripts/import-sla.py', // Python script
            $baseFile, // Base file
            $categoryFile, // Import file
            '--page ' . $page_number,
            '--output ' . $processedFile,
            '--masterpage category_' . $season . '_' . $category,
        ];

        $count++;

        exec(implode(' ', $command), $result);

        if ($debug && !empty($result)) {
            printResult($result);
        }
    }

    /**************************************************************************/

    /**
     * Replacing all instances of pattern %%YEAR%% with current year
     */

    echo('Replacing all instances of pattern %%YEAR%% with current year' . "\n");

    $pattern = '%%YEAR%%';

    $command = [
        'python ./scripts/replace-year.py', // Python script
        $processedFile, // (processed) base file
        '--pattern ' . $pattern,
    ];

    exec(implode(' ', $command), $result);

    if ($debug && !empty($result)) {
        printResult($result);
    }

    /**************************************************************************/

    /**
     * Generating `.pdf` file for review & copying `.sla` file for proposed changes
     *
     * `ISSUE/dist/templates/processed.sla` >> `ISSUE/dist/documents/raw.pdf`
     *
     * TODO: Until ScribusGenerator doesn't stack dataList entries (for whatever reason),
     * this has to be done manually!
     */

    // echo('Generating `.pdf` file for review & copying `.sla` file for proposed changes' . "\n");

    // $documentFile = $dist . '/documents/raw.pdf';

    // makePDF($processedFile, $documentFile);

    /**************************************************************************/

    /**
     * Copying processed `.sla` file, ready to be edited
     *
     * `ISSUE/dist/templates/processed.sla` >> `ISSUE/dist/templates/edited.sla`
     *
     */

    echo('Copying processed `.sla` file, ready to be edited' . "\n");

    copy($processedFile, $dist . '/templates/edited.sla');

} elseif (isset($argv[2]) && $argv[2] === '--build') {

    /**
     * Generating the final `.pdf` file after reviewing & editing by hand
     *
     * `ISSUE/dist/templates/edited.sla` >> `ISSUE/dist/documents/final.pdf`
     */

    $scribusFile = $dist . '/templates/edited.sla';
    $documentFile = $dist . '/documents/final.pdf';

    if (isset($argv[3]) && $argv[3] === '--all') {
        echo('Generating the final `.pdf` file' . "\n");

        makePDF($scribusFile, $documentFile);
    }

    /**************************************************************************/

    /**
     * Optimizing the final `.pdf` file with Ghostscript
     *
     * `ISSUE/dist/documents/bloated.pdf` >> `ISSUE/dist/optimized.pdf`
     *
     */

    echo('Optimizing the final `.pdf` file with Ghostscript' . "\n");

    $imageResolution = '200';
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

    if ($debug && !empty($result)) {
        printResult($result);
    }

    /**************************************************************************/

    /**
     * Generating `.eml` message drafts
     */

    echo('Generating `.eml` message drafts' . "\n");

    $seasonLocale = $season === 'spring'
        ? 'Frühling'
        : 'Herbst'
    ;

    $command = [
        'python ./scripts/get_books.py', // Python script
        '--input ' . $scribusFile,
        '--subject "Empfehlungsliste ' . $seasonLocale . ' ' . date('Y') . '"'
    ];

    exec(implode(' ', $command), $result);

    if ($debug && !empty($result)) {
        printResult($result);
    }

    echo('Finished!' . "\n");
} else {
    die('Please provide a valid issue identifier.' . "\n");
}
