<?php

declare(strict_types=1);

use Acme\BusinessRepository;

return [
    'lists only available businesses, by name' => function (): void {
        $names = array_column((new BusinessRepository(test_db()))->listAvailable(), 'name');
        assert_same(
            ['Bluefin Sushi Bar', 'Cedar Physio', 'Golden Gate Florist', 'Harbor Coffee Roasters', 'Lakeside Dental'],
            $names,
        );
    },
    'finds a business by id, pending included' => function (): void {
        $business = (new BusinessRepository(test_db()))->find(103);
        assert_same('Mission Street Hardware', $business['name']);
        assert_same('pending', $business['status']);
        assert_same(103, $business['id']);
    },
    'returns null for an unknown id' => function (): void {
        assert_same(null, (new BusinessRepository(test_db()))->find(999));
    },
];
