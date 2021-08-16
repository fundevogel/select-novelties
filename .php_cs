<?php

$finder = PhpCsFixer\Finder::create()
    ->exclude([
      'src',
      'dist'
    ])
    ->in(__DIR__)
;

return PhpCsFixer\Config::create()
    ->setRules([
        '@PSR2' => true,
        'array_syntax' => ['syntax' => 'short'],
    ])
    ->setFinder($finder)
;
