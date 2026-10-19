<?php /** @var list<array> $businesses */ use Acme\Http; ?>
<div class="page-head">
    <h1>Businesses</h1>
    <button type="button" class="btn btn-primary" id="add-business">+ Add business</button>
</div>

<label class="filter">
    <span>Filter</span>
    <input type="search" id="business-filter" placeholder="Name or city">
</label>

<?php if ($businesses === []): ?>
    <p class="empty">No businesses yet.</p>
<?php else: ?>
    <table class="table" id="business-table">
        <thead>
        <tr><th>Name</th><th>Category</th><th>City</th><th>Website</th></tr>
        </thead>
        <tbody>
        <?php foreach ($businesses as $b): ?>
            <tr data-search="<?= Http::e(mb_strtolower($b['name'] . ' ' . $b['city'])) ?>">
                <td><?= Http::e($b['name']) ?></td>
                <td><span class="pill"><?= Http::e($b['category']) ?></span></td>
                <td><?= Http::e($b['city']) ?></td>
                <td><?php if ($b['website']): ?><a href="<?= Http::e($b['website']) ?>" rel="noopener"><?= Http::e(parse_url($b['website'], PHP_URL_HOST)) ?></a><?php endif ?></td>
            </tr>
        <?php endforeach ?>
        </tbody>
    </table>
<?php endif ?>
