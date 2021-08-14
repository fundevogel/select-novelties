#!/usr/bin/env php

<?php

require_once('vendor/autoload.php');

use Pcbis\Webservice;
use Pcbis\Helpers\Butler;


class FetchApi
{
    /**
     * Current issue
     *
     * @var string
     */
    private $issue;


    /**
     * Modus operandi
     *
     * @var string
     */
    private $mode;


    /**
     * Source path
     *
     * @var string
     */
    private $root;


    /**
     * Destination path
     *
     * @var string
     */
    private $dist;


    /**
     * JSON source files
     *
     * @var array
     */
    private $files;


    /**
     * Failed API calls
     *
     * @var array
     */
    private $failures = [];


    /**
     * Object granting access to KNV's API
     *
     * @var \Pcbis\Webservice
     */
    private $api = null;


    /**
     * Age ratings
     *
     * @var array
     */
    private $ages = [];


    /**
     * Constructor
     *
     * @param string $issue Current issue
     * @param string $mode Modus operandi
     * @return void
     */
    public function __construct($issue, $mode)
    {
        # Determine issue
        $this->issue = $this->getIssue($issue);

        # Determine mode
        $this->mode = $mode;

        # Set paths
        # (1) Base path
        $this->base = $this->getBase($issue);

        # (2) Source & destination path
        $this->root = $this->base . '/src';
        $this->dist = $this->base . '/dist';

        # Determine source files
        $this->files = glob($this->root . '/json/*.json');

        # Authenticate with KNV's API
        # (1) Load credentials
        $credentials = json_decode(file_get_contents(__DIR__ . '/../../login.json'), true);

        # (2) Initialize API
        $this->api = new Webservice($credentials, $this->dist . '/.cache');
    }


    /**
     * Main function
     *
     * @return void
     */
    public function run(): void
    {
        if ($this->mode === 'fetching') {
            foreach ($this->files as $file) {
                # Load data from JSON file
                $data = json_decode(file_get_contents($file), true);

                // # Determine category
                // $category = $this->getCategory($file);

                # Retrieve data for all books
                foreach ($data as $item) {
                    $isbn = $item['ISBN'];

                    echo sprintf('Processing "%s":', $isbn);
                    echo "\n";

                    echo 'Fetching data from API ..';

                    try {
                        # Fetch bibliographic data from API
                        $book = $this->api->load($isbn);

                        # Determine age recommendation
                        $age = $book->age();

                        # Handle empty age ratings
                        if ($age === '') {
                            $age = 'Keine Altersangabe';
                        }

                        # Store age rating (if inappropriate)
                        if (Butler::contains($age, 'angabe') || Butler::contains($age, 'bis')) {
                            $this->ages[$isbn] = $age;
                        }

                        echo ' done.';
                        echo "\n";

                    } catch (Exception $e) {
                        # Add ISBN when fetching data fails
                        $this->failures['data'][] = $isbn;

                        echo ' failed!';
                        echo "\n";
                    }

                    echo 'Downloading cover ..';

                    # Download book cover
                    # (1) Set download path
                    $book->setImagePath($this->dist . '/images');

                    # (2) Download image file
                    if ($book->downloadCover(Butler::slug($book->title())) === false) {
                        # Add ISBN when download fails
                        $this->failures['cover'][] = $isbn;
                    }

                    echo ' done.';
                    echo "\n";
                    echo "\n";
                }

                echo 'Process complete!';
                echo "\n";
                echo "\n";

                # Save data for further processing
                # (1) Store age ratings
                $this->jsonStore($this->ages, $this->base . '/config/age-ratings.json');

                # (2) Store failed ISBNs
                $this->jsonStore($this->failures, $this->base . '/meta/failures.json');
            }
        }

        if ($this->mode === 'processing') {
            # Code here
        }
    }


    /**
     * Helpers
     */

    private function getIssue($issue)
    {
        if (!isset($issue)) {
            $year = date('Y');

            $issue = date('m') <= '06'
                ? $year . '-01'
                : $year . '-02'
            ;
        }

        return $issue;
    }


    private function getBase(string $issue): string
    {
        return realpath(dirname(__DIR__) . '/../issues/' . $issue);
    }


    private function getCategory(string $file): string
    {
        return basename(explode('.', $file)[0]);
    }


    private function jsonStore(array $data, string $file): void
    {
        # Store data as JSON file
        # (1) Create file handle
        $file = fopen($file, 'w');

        # (2) Write JSON data
        fwrite($file, json_encode($data, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));

        # (3) Close file handle
        fclose($file);
    }
}


$issue = null;

if (isset($argv[1])) {
    $issue = $argv[1];
}

$mode = null;

if (isset($argv[2])) {
    $mode = $argv[2];
}

$object = (new FetchApi($issue, $mode))->run();
