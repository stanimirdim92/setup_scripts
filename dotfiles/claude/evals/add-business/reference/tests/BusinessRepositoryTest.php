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
    'a created business stays hidden until its enrichment completes' => function (): void {
        $repository = new BusinessRepository(test_db());
        $business = $repository->createPending(fixture_places()->details('plc_F203'), 'note', 'REQ-TEST01');
        assert_same('pending', $business['status']);
        assert_true(!in_array('Tidewater Books', array_column($repository->listAvailable(), 'name'), true));

        assert_same(1, $repository->completeOpenEnrichments());
        assert_true(in_array('Tidewater Books', array_column($repository->listAvailable(), 'name'), true));
        assert_same('pending', $repository->find(103)['status'], 'a pending business without a request stays pending');
        assert_same(0, $repository->completeOpenEnrichments());
    },
];
