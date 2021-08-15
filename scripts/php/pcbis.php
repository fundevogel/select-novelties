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
    private $failures = [];


    /**
     * Object granting access to KNV's API
     *
     * @var \Pcbis\Webservice
     */
    private $api = null;


    /**
     * Constructor
     *
     * @param string $issue Current issue
     * @param string $mode Modus operandi
     * @throws Exception
     * @return void
     */
    public function __construct($issue, $mode)
    {
        if ($issue === null || $mode === null) {
            throw new Exception('Please enter valid parameters.');
        }

        # Determine issue
        $this->issue = $issue;

        # Determine mode
        $this->mode = $mode;

        # Set paths
        # (1) Base path
        $this->base = realpath(dirname(__DIR__) . '/../issues/' . $issue);

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
                            $this->ageRatings[$isbn] = $age;
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
                $this->jsonStore($this->ageRatings, $this->base . '/config/age-ratings.json');

                # (2) Store failed ISBNs
                $this->jsonStore($this->failures, $this->base . '/meta/failures.json');
            }
        }

        if ($this->mode === 'processing') {
            if (file_exists($ageRatingsFile = $this->base . '/config/age-ratings.json')) {
                $this->ageRatings = json_decode(file_get_contents($ageRatingsFile), true);
            }

            if (file_exists($duplicatesFile = $this->base . '/config/duplicates.json')) {
                $duplicates = json_decode(file_get_contents($duplicatesFile), true);
            }

            foreach ($this->files as $file) {
                # Prevent duplicate ISBNs per category
                $isbns =  [];

                # Load data from JSON file
                $raw = json_decode(file_get_contents($file), true);

                # Determine category
                $category = basename(explode('.', $file)[0]);

                $data  = [];

                # Retrieve data for every book
                foreach ($raw as $item) {
                    $isbn = $item['ISBN'];

                    # Block duplicate ISBNs across category
                    if (in_array($isbn, $isbns) === true) {
                        echo 'Blocked category duplicate: ' . $isbn;
                        continue;
                    }

                    # Block duplicate ISBNs across categories
                    if (isset($duplicates[$isbn]) && in_array($category, $duplicates[$isbn])) {
                        echo 'Blocked global duplicate: ' . $isbn;
                        continue;
                    }

                    echo sprintf('Processing "%s" ..', $isbn);

                    # Setup basic information
                    # (1) International Standard Book Number
                    # (2) Keep comma-separated author (for sorting)
                    $node = [
                        'ISBN' => $isbn,
                        'order' => $item['AutorIn'],
                    ];

                    try {
                        # Fetch bibliographic data from API
                        $book = $this->api->load($isbn);

                        # Combine all information
                        $node['AutorInnen'] = $book->author();
                        $node['Kopfleiste'] = $this->buildHeading($book);
                        $node['Inhaltsbeschreibung'] = $this->buildDescription($book);
                        $node['Mitwirkende'] = $this->buildParticipants($book);
                        $node['Informationen'] = $this->buildInformation($book);
                        $node['Abschluss'] = $this->buildClosing($book);
                        $node['Preis'] = $book->retailPrice();
                        $node['@Cover'] = Butler::slug($book->title()) . '.jpg';

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
                $data = Butler::sort($data, 'order', 'asc');

                # Create updated JSON file
                $this->jsonStore($data, $this->dist . '/json/' . $category . '.json');

                # Create updated CSV file
                Pcbis\Spreadsheets::array2csv($data, $this->dist . '/csv/' . $category . '.csv');
            }
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
                ' und',
                $book->dimensions(),
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

    private function jsonStore(array $data, string $file): void
    {
        # Store data as JSON file
        # (1) Create file handle
        $file = fopen($file, 'w');

        # (2) Write JSON data
        fwrite($file, json_encode(array_values($data), JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));

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
