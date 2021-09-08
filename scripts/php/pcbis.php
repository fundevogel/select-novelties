<?php

require_once('vendor/autoload.php');

use Pcbis\Webservice;
use Pcbis\Helpers\Butler;


class KNVClient
{
    /**
     * Modus operandi
     *
     * @var string
     */
    private $mode;


    /**
     * Current issue
     *
     * @var string
     */
    private $issue;


    /**
     * Current category
     *
     * @var string
     */
    private $category;


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
     * JSON source file
     *
     * @var str
     */
    private $file;


    /**
     * Age ratings
     *
     * @var array
     */
    private $ageRatings = [];


    /**
     * Failed API calls
     *
     * @var array
     */
    private $failures = [
        'data' => [],
        'cover' => [],
    ];


    /**
     * Object granting access to KNV's API
     *
     * @var \Pcbis\Webservice
     */
    private $api = null;


    /**
     * Constructor
     *
     * @param string $mode Modus operandi
     * @param string $issue Current issue
     * @param string $category Current category
     * @throws Exception
     * @return void
     */
    public function __construct($mode, $issue, $category)
    {
        if ($mode === null || $issue === null || $category === null) {
            throw new Exception('Please enter valid parameters.');
        }

        # Determine mode
        $this->mode = $mode;

        # Determine issue
        $this->issue = $issue;

        # Determine category
        $this->category = $category;

        # Set paths
        # (1) Base path
        $this->base = realpath(dirname(__DIR__) . '/../issues/' . $issue);

        # (2) Source & destination path
        $this->root = $this->base . '/src';
        $this->dist = $this->base . '/dist';

        # Authenticate with KNV's API
        # (1) Load credentials
        $credentials = json_decode(file_get_contents(__DIR__ . '/../../login.json'), true);

        # (2) Initialize API
        $this->api = new Webservice($credentials, __DIR__ . '/../../.cache');
    }


    /**
     * Main function
     *
     * @return void
     */
    public function run(): void
    {
        if ($this->mode === 'fetching') {
            # Determine source file
            if (!file_exists($file = $this->root . '/csv/' . $this->category . '.csv')) {
                throw new Exception(sprintf('Invalid file: "%s"', $file));
            }

            # Load data from JSON file
            $headers = [
                'AutorIn',
                'Titel',
                'Verlag',
                'ISBN',
                'Einband',
                'Preis',
                'Meldenummer',
                'SortRabatt',
                'Gewicht',
                'Informationen',
                'Zusatz',
                'Kommentar'
            ];

            $data = [];

            # Retrieve data for all books
            foreach (Pcbis\Spreadsheets::csvOpen($file, $headers) as $item) {
                $isbn = $item['ISBN'];

                echo sprintf('Processing "%s":', $isbn);
                echo "\n";

                echo 'Fetching data from API ..';

                try {
                    # Fetch bibliographic data from API
                    $book = $this->api->load($isbn);

                    # Export dataset
                    $set = array_merge([
                        'ISBN' => $isbn,
                        'Sortierung' => $item['AutorIn'],
                    ], $book->export());

                    # Determine age recommendation ..
                    $age = '';

                    # .. (1) except for calendars
                    if (!$book->isCalendar()) {
                        $age = $book->age();

                        # Handle empty age ratings
                        if ($age === '') {
                            $age = 'Keine Altersangabe';
                        }
                    }

                    # .. (2) and apply it
                    $set['Altersempfehlung'] = $age;

                    $data[] = $set;

                    echo ' done.';
                    echo "\n";

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

                } catch (Exception $e) {
                    # Add ISBN when fetching data fails
                    $this->failures['data'][] = $isbn;

                    echo ' failed!';
                    echo "\n";
                }
            }

            echo 'Process complete!';
            echo "\n";
            echo "\n";

            # Save data for further processing
            # (1) Store dadasets
            $this->jsonStore($data, $this->root . '/json/' . $this->category . '.json', true);

            # (2) Store failed ISBNs
            $this->jsonStore($this->failures, $this->base . '/meta/failures.json');
        }

        if ($this->mode === 'processing') {
            # Determine source file
            if (!file_exists($file = $this->root . '/json/' . $this->category . '.json')) {
                throw new Exception(sprintf('Invalid file: "%s"', $file));
            }

            # Load age ratings
            if (file_exists($ageRatingsFile = $this->base . '/config/age-ratings.json')) {
                $this->ageRatings = json_decode(file_get_contents($ageRatingsFile), true);
            }

            # Load duplicates file
            if (file_exists($duplicatesFile = $this->base . '/config/duplicates.json')) {
                $duplicates = json_decode(file_get_contents($duplicatesFile), true);
            }

            # Prevent duplicate ISBNs per category
            $isbns =  [];

            # Load data from JSON file
            $raw = json_decode(file_get_contents($file), true);

            $data  = [];

            # Retrieve data for every book
            foreach ($raw as $item) {
                $isbn = $item['ISBN'];

                # Block duplicate ISBNs across category
                if (in_array($isbn, $isbns) === true) {
                    continue;
                }

                # Block duplicate ISBNs across categories
                if (isset($duplicates[$isbn]) && in_array($this->category, $duplicates[$isbn])) {
                    continue;
                }

                echo sprintf('Processing "%s" ..', $isbn);

                # Setup basic information
                # (1) International Standard Book Number
                # (2) Keep comma-separated author (for sorting)
                $node = [
                    'ISBN' => $isbn,
                    'Sortierung' => $item['Sortierung'],
                ];

                try {
                    # Fetch bibliographic data from API
                    $book = $this->api->load($isbn);

                    # Combine all information for ..
                    # (1) .. template files
                    $node['AutorInnen'] = $book->author();
                    $node['Kopfleiste'] = $this->buildHeading($book);
                    $node['Inhaltsbeschreibung'] = $this->buildDescription($book);
                    $node['Mitwirkende'] = $this->buildParticipants($book);
                    $node['Informationen'] = $this->buildInformation($book);
                    $node['Abschluss'] = $this->buildClosing($book);
                    $node['Preis'] = $book->retailPrice();
                    $node['@Cover'] = Butler::slug($book->title()) . '.jpg';

                    # (2) .. general use
                    $node['Titel'] = $book->title();
                    $node['Untertitel'] = $book->subtitle();
                    $node['Verlag'] = $book->publisher();

                    # Store data record
                    $data[]  = $node;

                    # Mark ISBN as processed
                    $isbns[]  = $isbn;

                    echo ' done.';
                    echo "\n";

                } catch (\Exception $e) {
                    echo ' failed!';
                    echo "\n";
                }
            }

            # Sort by author's last name
            $data = Butler::sort($data, 'Sortierung', 'asc');

            # Create updated JSON file
            $this->jsonStore($data, $this->dist . '/json/' . $this->category . '.json', true);
        }
    }


    private function buildHeading(\Pcbis\Products\Product $book): string
    {
        # Determine title & subtitle
        # (1) Store title
        $heading = $book->title();

        # (2) Add subtitle (if present)
        $subtitle = $book->subtitle();

        if (!empty($subtitle)) {
            $heading .= '. ' . $subtitle;
        }

        return $heading;
    }


    private function buildDescription(\Pcbis\Products\Product $book): string
    {
        # Store all available descriptions as string
        return Butler::join($book->description(true), "\n");
    }


    private function buildParticipants($book): string
    {
        $participants = '';

        # TODO: Determine involved people
        // $people = [
        //     $book->illustrator(),
        //     $book->drawer(),
        //     $book->photographer(),
        //     $book->translator(),
        //     $book->editor(),
        //     $book->participant(),
        //     $book->original(),
        // ];

        // $participants = '';

        # TODO: Determine involved people
        // $people = [
        //     $book->narrator(),
        //     $book->composer(),
        //     $book->producer(),
        //     $book->director(),
        //     $book->participant(),
        // ];

        // $participants = '';

        // $participants = $book->author();

        return $participants;
    }


    private function buildInformation(\Pcbis\Products\Product $book): string
    {
        # Build info string
        $year = $book->releaseYear();
        $publisher = $book->publisher();

        # Determine preposition, depending on publisher
        $preposition = 'bei';

        if (Butler::contains(Butler::lower($publisher), 'verlag')) {
            $preposition = 'im';
        }

        $info = Butler::join([$year, $preposition, $publisher, 'erschienen'], ' ');

        # Build information depending on category
        $specifics = '.';

        if ($book->isBook()) {
            $specifics = Butler::join([
                ';',
                $book->binding(),
                'und',
                $book->pageCount(),
                'Seiten stark',
            ], ' ');
        }

        if ($book->isMedia()) {
            $specifics = Butler::join([';', $book->duration()], ' ');
        }

        if ($book->isCalendar()) {
            # TODO: Add dimensions
            $specifics = Butler::join([
                'und',
                $book->dimensions() . 'cm',
                'groß'
            ], ' ');
        }

        return $info . $specifics . '.';
    }


    private function buildClosing(\Pcbis\Products\Product $book): string
    {
        $isbn = $book->isbn();

        if ($book->isCalendar()) {
            return $isbn;
        }

        # Determine age recommendation
        $age = isset($this->ageRatings[$isbn])
            ? $this->ageRatings[$isbn]
            : $book->age()
        ;

        return $isbn . ' - ' . $age;
    }


    /**
     * Shared
     */

    private function jsonStore(array $data, string $file, bool $valuesOnly = false): void
    {
        if ($valuesOnly === true) {
            $data = array_values($data);
        }

        # Store data as JSON file
        # (1) Create file handle
        $file = fopen($file, 'w');

        # (2) Write JSON data
        fwrite($file, json_encode($data, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));

        # (3) Close file handle
        fclose($file);
    }
}


$mode = null;

if (isset($argv[1])) {
    $mode = $argv[1];
}

$issue = null;

if (isset($argv[2])) {
    $issue = $argv[2];
}

$category = null;

if (isset($argv[3])) {
    $category = $argv[3];
}

$object = (new KNVClient($mode, $issue, $category))->run();
