<?php
/** PI-12: la firma generada por el plugin PHP de WordPress es aceptada por la API Python (integración real). */
require __DIR__ . '/../../wordpress-plugin/dsm-oirs-formularios/includes/firma.php';
$api = getenv('OIRS_API_URL') ?: 'http://127.0.0.1:8000/';
$secreto = getenv('WP_HMAC_SECRET');
$datos = ['tipo' => 'CONSULTA', 'establecimiento' => 'CESFAM-CON', 'descripcion' => 'Consulta enviada desde el plugin PHP de WordPress.',
          'nombre' => 'Prueba PHP', 'email' => 'php@example.com', 'acepta_tratamiento_datos' => true];
$cuerpo = json_encode($datos, JSON_UNESCAPED_UNICODE);
function enviar($api, $cuerpo, $ts, $firma) {
    $ch = curl_init($api . 'api/v1/publico/requerimientos');
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $cuerpo, CURLOPT_RETURNTRANSFER => true, CURLOPT_NOPROXY => '*',
        CURLOPT_HTTPHEADER => ['Content-Type: application/json', "X-OIRS-Timestamp: $ts", "X-OIRS-Firma: $firma"]]);
    $r = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    return [$code, $r];
}
$ts = time();
[$c1, $r1] = enviar($api, $cuerpo, $ts, dsm_oirs_firmar($cuerpo, $ts, $secreto));
[$c2, $r2] = enviar($api, $cuerpo, $ts, dsm_oirs_firmar($cuerpo, $ts, 'secreto-incorrecto'));
echo "Firma válida   -> HTTP $c1 $r1\n";
echo "Firma inválida -> HTTP $c2 $r2\n";
$ok = ($c1 === 201 && $c2 === 401);
echo $ok ? "PI-12 APROBADO\n" : "PI-12 RECHAZADO\n";
exit($ok ? 0 : 1);
