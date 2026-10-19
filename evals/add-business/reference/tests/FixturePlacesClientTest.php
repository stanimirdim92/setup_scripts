<?php

declare(strict_types=1);

use Acme\Places\PlacesUnavailable;

return [
    'search matches the name, case-insensitive' => function (): void {
        $names = array_map(fn ($p) => $p->name, fixture_places()->search('tidewater'));
        assert_same(['Tidewater Books'], $names);
    },
    'search is multi-token across name, street, ZIP, city and category' => function (): void {
        $ids = fn (string $q): array => array_map(fn ($p) => $p->placeId, fixture_places()->search($q));
        assert_same(['plc_F202'], $ids('sunrise oakland'));
        assert_same(['plc_F201'], $ids('sunrise, 94122'));
        assert_same(['plc_F201'], $ids('irving'));
        assert_same(['plc_F204'], $ids('gym'));
        assert_same([], $ids('sunrise berkeley'));
    },
    'details finds a place by id' => function (): void {
        $place = fixture_places()->details('plc_F201');
        assert_same('Sunrise Bakery', $place?->name);
        assert_same('94122', $place?->zip);
    },
    'details returns null for an unknown id' => function (): void {
        assert_same(null, fixture_places()->details('plc_nope'));
    },
    'fail mode throws PlacesUnavailable' => function (): void {
        assert_throws(PlacesUnavailable::class, fn () => fixture_places(fail: true)->search('sunrise'));
    },
];
