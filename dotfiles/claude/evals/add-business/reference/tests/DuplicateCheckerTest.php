<?php

declare(strict_types=1);

use Acme\BusinessRepository;
use Acme\DuplicateChecker;

function rule_for(string $placeId): ?string
{
    $checker = new DuplicateChecker((new BusinessRepository(test_db()))->all());
    return $checker->find(fixture_places()->details($placeId))['rule'] ?? null;
}

return [
    'root domain drops scheme, www, subdomains and path' => function (): void {
        assert_same('bluefinsushi.com', DuplicateChecker::rootDomain('http://order.bluefinsushi.com/menu'));
        assert_same('bluefinsushi.com', DuplicateChecker::rootDomain('https://WWW.BlueFinSushi.com/'));
        assert_same('example.co.uk', DuplicateChecker::rootDomain('shop.example.co.uk'));
        assert_same(null, DuplicateChecker::rootDomain(null));
    },
    'name and phone normalization' => function (): void {
        assert_same('golden gate florist', DuplicateChecker::name(' Golden Gate  florist!'));
        assert_same('4155550142', DuplicateChecker::phone('+1 (415) 555-0142'));
        assert_same(null, DuplicateChecker::phone('555-0142'));
    },
    'each rule matches its fixture place' => function (): void {
        assert_same('domain', rule_for('plc_F101'));
        assert_same('name_zip', rule_for('plc_F102'));
        assert_same('place_id', rule_for('plc_A003'));
        assert_same('cid', rule_for('plc_F104'));
        assert_same('phone', rule_for('plc_F105'));
    },
    'a new place matches nothing' => function (): void {
        assert_same(null, rule_for('plc_F201'));
        assert_same(null, rule_for('plc_F204'));
    },
];
