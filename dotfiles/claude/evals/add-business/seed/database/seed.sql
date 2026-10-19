-- Fixed seed rows. Tests depend on them; do not change them.
INSERT INTO businesses (id, name, place_id, cid, street, zip, city, category, website, phone, maps_url, status) VALUES
    (101, 'Bluefin Sushi Bar', 'plc_A001', '5550101', '1200 Market St', '94102', 'San Francisco', 'Restaurant', 'https://www.bluefinsushi.com/', '(415) 555-0101', 'https://www.google.com/maps?cid=5550101', 'available'),
    (102, 'Golden Gate Florist', 'plc_A002', '5550102', '88 Valencia St', '94110', 'San Francisco', 'Florist', 'https://goldengateflowers.com', '(415) 555-0102', 'https://www.google.com/maps?cid=5550102', 'available'),
    (103, 'Mission Street Hardware', 'plc_A003', '5550103', '2290 Mission St', '94110', 'San Francisco', 'Hardware store', 'https://missionhardware.com', '(415) 555-0103', 'https://www.google.com/maps?cid=5550103', 'pending'),
    (104, 'Harbor Coffee Roasters', 'plc_A004', '5550104', '1 Ferry Building', '94111', 'San Francisco', 'Coffee shop', 'https://harborcoffee.com', '(415) 555-0104', 'https://www.google.com/maps?cid=5550104', 'available'),
    (105, 'Cedar Physio', 'plc_A005', '5550105', '19 Cedar St', '94109', 'San Francisco', 'Physical therapist', 'https://cedarphysio.com', '(415) 555-0142', 'https://www.google.com/maps?cid=5550105', 'available'),
    (106, 'Lakeside Dental', 'plc_A006', '5550106', '300 Grand Ave', '94612', 'Oakland', 'Dentist', 'https://lakesidedental.com', '(510) 555-0106', 'https://www.google.com/maps?cid=5550106', 'available');
