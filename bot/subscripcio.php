<?php
// SPDX-License-Identifier: AGPL-3.0-or-later
// Altes, canvis i baixes dels avisos de Temps a Montflorit al navegador
// (ADR 0048). A IONOS, app/meteo-local/subscripcio.php només el carrega des de
// la còpia del repositori (bot/instalar.sh): s'actualitza sol amb el git pull.
// Desa a ~/.temps-bot/push.json, amb el mateix cadenat que bot/push.py, que
// és qui envia. De cada dispositiu només es desa l'adreça que dona el seu
// navegador per enviar-li notificacions i el que tria: res de qui és.
//
// GET              la clau pública (VAPID) per subscriure's
// POST {accio: "desa", subscripcio: {endpoint, keys}, avisos, resum, idioma}
// POST {accio: "estat" | "prova" | "baixa", endpoint}

date_default_timezone_set('Europe/Madrid');
const ORIGENS = ['https://meteo-montflorit.github.io'];
// Els trens i el trànsit no són avisos: es consulten (ADR 0053).
const TIPUS = ['riera', 'perill', 'pluja'];
const HORES = ['', '6', '7', '8', '21'];
const IDIOMES = ['ca', 'es'];
// Els serveis de notificacions dels navegadors: cap altra adreça s'accepta.
const SERVEIS = '/^https:\/\/(fcm\.googleapis\.com|android\.googleapis\.com|[a-z0-9.-]*push\.services\.mozilla\.com'
    . '|web\.push\.apple\.com|[a-z0-9.-]*\.notify\.windows\.com)\//';
const MAXIM = 20000;            // subscripcions en total
const COS_MAXIM = 4096;

$base = defined('TEMPS_BOT') ? TEMPS_BOT : dirname(__DIR__, 2) . '/.temps-bot';
$origen = $_SERVER['HTTP_ORIGIN'] ?? '';
// La web publicada i, per provar-la, la mateixa servida des de l'ordinador.
if (in_array($origen, ORIGENS, true) || preg_match('/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/', $origen)) {
    header('Access-Control-Allow-Origin: ' . $origen);
    header('Vary: Origin');
}
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function respon($codi, $dades) {
    http_response_code($codi);
    echo json_encode($dades, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

$metode = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($metode === 'OPTIONS') {
    header('Access-Control-Allow-Methods: GET, POST');
    header('Access-Control-Allow-Headers: Content-Type');
    respon(204, null);
}
if ($metode === 'GET') {
    $claus = json_decode(@file_get_contents("$base/vapid.json"), true);
    if (!$claus || empty($claus['publica'])) respon(503, ['error' => 'sense claus']);
    respon(200, ['clau' => $claus['publica']]);
}
if ($metode !== 'POST') respon(405, ['error' => 'mètode']);

$cru = file_get_contents('php://input', false, null, 0, COS_MAXIM + 1);
if ($cru === false || strlen($cru) > COS_MAXIM) respon(413, ['error' => 'massa llarg']);
$p = json_decode($cru, true);
if (!is_array($p)) respon(400, ['error' => 'json']);
$accio = $p['accio'] ?? '';
$endpoint = $accio === 'desa' ? ($p['subscripcio']['endpoint'] ?? '') : ($p['endpoint'] ?? '');
if (!is_string($endpoint) || strlen($endpoint) > 1000 || !preg_match(SERVEIS, $endpoint)) {
    respon(400, ['error' => 'adreça']);
}

$cadenat = fopen("$base/push.lock", 'a');
flock($cadenat, LOCK_EX);
$subs = json_decode(@file_get_contents("$base/push.json"), true) ?: [];

function desa_subs($base, $subs) {
    $tmp = "$base/push.json.tmp";
    file_put_contents($tmp, json_encode($subs, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    rename($tmp, "$base/push.json");
}

function opcions($s) {
    return ['avisos' => $s['avisos'], 'resum' => $s['resum'] ?? '', 'idioma' => $s['idioma']];
}

if ($accio === 'desa') {
    $claus = $p['subscripcio']['keys'] ?? [];
    $b64 = '/^[A-Za-z0-9_-]+={0,2}$/';
    if (!is_string($claus['p256dh'] ?? null) || !is_string($claus['auth'] ?? null)
        || !preg_match($b64, $claus['p256dh']) || !preg_match($b64, $claus['auth'])
        || strlen($claus['p256dh']) > 120 || strlen($claus['auth']) > 40) {
        respon(400, ['error' => 'claus']);
    }
    $avisos = array_values(array_intersect(TIPUS, is_array($p['avisos'] ?? null) ? $p['avisos'] : []));
    $resum = (string)($p['resum'] ?? '');
    // Una pàgina vella encara pot enviar les 20 h: ara són les 21 h (ADR 0053).
    if ($resum === '20') $resum = '21';
    $idioma = (string)($p['idioma'] ?? 'ca');
    if (!in_array($resum, HORES, true) || !in_array($idioma, IDIOMES, true)) respon(400, ['error' => 'opcions']);
    $nou = !isset($subs[$endpoint]);
    if ($nou && count($subs) >= MAXIM) respon(503, ['error' => 'ple']);
    $subs[$endpoint] = ['keys' => ['p256dh' => $claus['p256dh'], 'auth' => $claus['auth']],
                        'avisos' => $avisos, 'resum' => $resum, 'idioma' => $idioma,
                        'alta' => $subs[$endpoint]['alta'] ?? date('Y-m-d')]
                       + (isset($subs[$endpoint]['prova']) ? ['prova' => $subs[$endpoint]['prova']] : []);
    desa_subs($base, $subs);
    respon(200, ['ok' => true, 'nou' => $nou] + opcions($subs[$endpoint]));
}
if ($accio === 'estat') {
    if (!isset($subs[$endpoint])) respon(404, ['ok' => false]);
    respon(200, ['ok' => true] + opcions($subs[$endpoint]));
}
if ($accio === 'prova') {
    if (!isset($subs[$endpoint])) respon(404, ['ok' => false]);
    $subs[$endpoint]['prova'] = date('c');
    desa_subs($base, $subs);
    respon(200, ['ok' => true]);
}
if ($accio === 'baixa') {
    unset($subs[$endpoint]);
    desa_subs($base, $subs);
    respon(200, ['ok' => true]);
}
respon(400, ['error' => 'acció']);
