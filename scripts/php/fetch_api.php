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
     * CSV source files
     *
     * @var array
     */
    private $files;


    /**
     * Per-category blocklist
     *
     * @var array
     */
    private $blockList = [];


    /**
     * Suitable age recommendations
     *
     * @var array
     */
    private $properAges = [];


    /**
     * Object granting access to KNV's API
     *
     * @var \Pcbis\Webservice
     */
    private $api = null;


    /**
     * Failed API calls
     *
     * @var array
     */
    private $failures = [];


    /**
     * Constructor
     *
     * @param string $issue Current issue
     * @return void
     */
    public function __construct(string $issue = null)
    {
        # Determine issue
        if (!isset($issue)) {
            $year = date('Y');

            $issue = date('m') <= '06'
                ? $year . '-01'
                : $year . '-02'
            ;
        }

        $this->issue = $issue;

        # Set paths
        # (1) Base path
        $this->base = realpath(dirname(__DIR__) . '/../issues/' . $this->issue);

        # (2) Source & destination path
        $this->root = $this->base . '/src';
        $this->dist = $this->base . '/dist';

        # Determine source files
        $this->files = glob($this->root . '/csv/*.csv');

        # Fetch modifications
        # (1) Load list of ISBNs to be blocked per category, useful if they exist twice
        if (file_exists($blockListFile = $this->base . '/config/block-list.json')) {
            $this->blockList = json_decode(file_get_contents($blockListFile), true);
        }

        # (2) Load list of age recommendations, replacing improper ones
        if (file_exists($properAgesFile = $this->base . '/config/proper-ages.json')) {
            $this->properAges = json_decode(file_get_contents($properAgesFile), true);
        }

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
        foreach ($this->files as $file) {
            # Load raw CSV file as exported via pcbis.de
            $raw = Pcbis\Spreadsheets::csv2array($file, ';');

            # Determine category
            $category = basename(explode('.', $file)[0]);

            $data  = [];

            # Retrieve data for every book
            foreach ($raw as $item) {
                # Skip blocked ISBNs
                if (isset($this->blockList[$category]) && in_array($item['ISBN'], $this->blockList[$category])) {
                    continue;
                }

                echo sprintf('Processing "%s":', $item['ISBN']);
                echo "\n";

                # Provide base information first
                # This is necessary when detecting improper age rating,
                # since books & audiobooks have different columns
                $node = [
                    'ISBN' => $item['ISBN'],
                    'AutorIn' => '',
                    'Titel' => '',
                    'Untertitel' => '',
                    'Preis' => '',
                    'Erscheinungsjahr' => '',
                    'Altersempfehlung' => '',
                    'Inhaltsbeschreibung' => '',
                ];

                echo 'Fetching data from API ..';

                try {
                    # Combine spreadsheet & API data
                    # (1) Fetch bibliographic data from API
                    $book = $this->api->load($item['ISBN']);

                    # (2) Merge both data sources
                    $node = array_merge($node, $book->export());

                    # Apply individual changes
                    # (1) Keep comma-separated author (for sorting)
                    $node['order'] = $item['AutorIn'];

                    # (2) Store all available descriptions as string
                    $node['Inhaltsbeschreibung'] = Butler::join($book->description(true), "\n");

                    echo ' done.';
                    echo "\n";

                } catch (\Exception $e) {
                    echo ' failed!';
                    echo "\n";

                    $this->failures[] = $item['ISBN'];
                }

                # Handle age recommendations ..
                # (1) .. that are empty
                if ($node['Altersempfehlung'] === '') {
                    $node['Altersempfehlung'] = 'Keine Altersangabe';
                }

                # (2) .. that are ambiguous
                if (isset($this->properAges[$item['ISBN']])) {
                    $node['Altersempfehlung'] = $this->properAges[$item['ISBN']];
                }

                echo 'Downloading cover ..';

                # Download book cover
                # (1) Set download path
                $book->setImagePath($this->dist . '/images');

                # (2) Download image file
                $imageName = Butler::slug($book->title());

                # (3) Store file name for later use ..
                $node['@Cover'] = $book->downloadCover($imageName)
                    # ..if download is successful
                    ? $imageName . '.jpg'
                    : ''
                ;

                echo ' done.';
                echo "\n";

                # Store data record
                $data[]  = $node;

                echo 'Process complete!';
                echo "\n";
                echo "\n";
            }

            # Sort by author's last name
            $data = Butler::sort($data, 'order', 'asc');

            # Create updated CSV file
            Pcbis\Spreadsheets::array2csv($data, $this->dist . '/csv/' . basename($file));

            # Store failed ISBNs
            if (!empty($this->failures)) {
                # (1) Create file handle
                # (2) Pretty-print results
                # (3) Close file handle
                $file = fopen($this->base . '/config/failures.json', 'w');
                fwrite($file, json_encode($this->failures, JSON_UNESCAPED_SLASHES|JSON_PRETTY_PRINT));
                fclose($file);
            }
        }
    }
}


$issue = null;

if (isset($argv[1])) {
    $issue = $argv[1];
}

$object = (new FetchApi($issue))->run();
