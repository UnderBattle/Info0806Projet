package com.example.info0806projet

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.net.TrafficStats
import android.net.wifi.WifiManager
import android.os.Bundle
import android.os.Environment
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.example.info0806projet.ui.theme.Info0806ProjetTheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream
import java.io.OutputStreamWriter

//Il faut une moyenne ecart type du réseau
class MainActivity : ComponentActivity(), SensorEventListener, LocationListener {

    private lateinit var sensorManager: SensorManager
    private var accelerometer: Sensor? = null
    private var humiditySensor: Sensor? = null
    private var temperatureSensor: Sensor? = null

    private var _accelX by mutableFloatStateOf(0f)
    private var _accelY by mutableFloatStateOf(0f)
    private var _accelZ by mutableFloatStateOf(0f)

    private var _humidity by mutableFloatStateOf(0f)
    private var _temperature by mutableFloatStateOf(0f)

    private lateinit var locationManager: LocationManager
    private var _latitude by mutableDoubleStateOf(0.0)
    private var _longitude by mutableDoubleStateOf(0.0)
    private var _vitesse by mutableDoubleStateOf(0.0) // Vitesse en km/h

    private var _wifiSSID by mutableStateOf("Non connecté")
    private var _wifiSignalStrength by mutableIntStateOf(0)

    private var _uploadSpeed by mutableLongStateOf(0L)
    private var _downloadSpeed by mutableLongStateOf(0L)

    private val collectedData = mutableStateListOf<Map<String, Any>>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestPermissionsIfNeeded()

        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        humiditySensor = sensorManager.getDefaultSensor(Sensor.TYPE_RELATIVE_HUMIDITY)
        temperatureSensor = sensorManager.getDefaultSensor(Sensor.TYPE_AMBIENT_TEMPERATURE)

        locationManager = getSystemService(LOCATION_SERVICE) as LocationManager

        setContent {
            val coroutineScope = rememberCoroutineScope()
            val context = LocalContext.current
            LaunchedEffect(Unit) {
                coroutineScope.launch {
                    while (true) {
                        getNetworkStats()
                        val (ssid, signal) = getWifiInfo(context)
                        _wifiSSID = ssid
                        _wifiSignalStrength = signal
                        collectedData.add(
                            mapOf(
                                "timestamp" to System.currentTimeMillis(),
                                "accelX" to _accelX,
                                "accelY" to _accelY,
                                "accelZ" to _accelZ,
                                "latitude" to _latitude,
                                "longitude" to _longitude,
                                "vitesse" to _vitesse,
                                "humidity" to _humidity,
                                "temperature" to _temperature,
                                "wifiSSID" to _wifiSSID,
                                "wifiSignalStrength" to _wifiSignalStrength,
                                "uploadSpeed" to _uploadSpeed,
                                "downloadSpeed" to _downloadSpeed
                            )
                        )
                        delay(2000L) // Refresh toutes les 2 secondes
                    }
                }
            }
            Info0806ProjetTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    DataScreen(
                        accelX = _accelX,
                        accelY = _accelY,
                        accelZ = _accelZ,
                        latitude = _latitude,
                        longitude = _longitude,
                        vitesse = _vitesse,
                        humidity = _humidity,
                        temperature = _temperature,
                        wifiSSID = _wifiSSID,
                        wifiSignalStrength = _wifiSignalStrength,
                        uploadSpeed = _uploadSpeed,
                        downloadSpeed = _downloadSpeed,
                        modifier = Modifier.padding(innerPadding)
                    )
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        requestPermissionsIfNeeded()
        accelerometer?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        humiditySensor?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        temperatureSensor?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        val (ssid, signal) = getWifiInfo(this)
        _wifiSSID = ssid
        _wifiSignalStrength = signal
        requestLocationUpdates()
    }

    override fun onPause() {
        super.onPause()
        sensorManager.unregisterListener(this)
        locationManager.removeUpdates(this)
    }

    override fun onSensorChanged(event: SensorEvent?) {
        event?.let {
            when (it.sensor.type) {
                Sensor.TYPE_ACCELEROMETER -> {
                    _accelX = it.values[0]
                    _accelY = it.values[1]
                    _accelZ = it.values[2]
                }
                Sensor.TYPE_RELATIVE_HUMIDITY -> {
                    _humidity = it.values[0]
                }
                Sensor.TYPE_AMBIENT_TEMPERATURE -> {
                    _temperature = it.values[0]
                }
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    @SuppressLint("MissingPermission")
    private fun requestLocationUpdates() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 2000L, 1f, this)
        }
    }

    override fun onLocationChanged(location: Location) {
        _latitude = location.latitude
        _longitude = location.longitude
        _vitesse = location.speed * 3.6 // Convertir m/s en km/h

        Log.d("GPS", "Latitude: $_latitude, Longitude: $_longitude, Vitesse brute: ${location.speed} m/s - Vitesse km/h: $_vitesse")
        Log.d("GPS", "Précision du GPS: ${location.accuracy} mètres")
    }

    @SuppressLint("MissingPermission")
    private fun getWifiInfo(context: Context): Pair<String, Int> {
        val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

        val network = connectivityManager.activeNetwork
        val capabilities = connectivityManager.getNetworkCapabilities(network)

        return if (capabilities != null && capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                @Suppress("DEPRECATION") val wifiInfo = wifiManager.connectionInfo
                val ssid = wifiInfo.ssid.removePrefix("\"").removeSuffix("\"") // Nettoyage du SSID
                val signalStrength = wifiInfo.rssi // Signal en dBm (-30 = fort, -90 = faible)
                Log.d("WiFi", "SSID: $ssid, Signal: $signalStrength dBm")
                Pair(ssid, signalStrength)
            } else {
                Log.e("WiFi", "Permission ACCESS_FINE_LOCATION manquante")
                Pair("Permission manquante", -100)
            }
        } else {
            Pair("Non connecté", -100)
        }
    }

    private fun getNetworkStats() {
        val txBytes = TrafficStats.getTotalTxBytes()
        val rxBytes = TrafficStats.getTotalRxBytes()
        _uploadSpeed = txBytes / 1024 // en KB
        _downloadSpeed = rxBytes / 1024 // en KB
    }
    private fun requestPermissionsIfNeeded() {
        val permissions = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        if (permissions.isNotEmpty()) {
            requestPermissions(permissions.toTypedArray(), 1)
        }
    }

    private fun sauvegarderCSV() {
        val nomFichier = "donnees_capteurs.csv"
        val dossierTelechargements = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
        val fichier = File(dossierTelechargements, nomFichier)

        try {
            val outputStream = FileOutputStream(fichier)
            val writer = OutputStreamWriter(outputStream)

            // En-tête du fichier CSV
            writer.append("Temps,Latitude,Longitude,Vitesse,AccélérationX,AccélérationY,AccélérationZ,Humidité,Température,WiFi SSID,Signal WiFi,Upload KB,Download KB\n")

            // Ajouter une ligne de données (à adapter avec tes variables)
            writer.append("${System.currentTimeMillis()},$_latitude,$_longitude,$_vitesse,$_accelX,$_accelY,$_accelZ,$_humidity,$_temperature,$_wifiSSID,$_wifiSignalStrength,$_uploadSpeed,$_downloadSpeed\n")

            writer.flush()
            writer.close()

            Log.d("CSV", "Fichier CSV enregistré : ${fichier.absolutePath}")
        } catch (e: Exception) {
            Log.e("CSV", "Erreur lors de l'enregistrement du fichier CSV", e)
        }
    }

    @Composable
    fun DataScreen(
        accelX: Float,
        accelY: Float,
        accelZ: Float,
        latitude: Double,
        longitude: Double,
        vitesse: Double,
        humidity: Float,
        temperature: Float,
        wifiSSID: String,
        wifiSignalStrength: Int,
        uploadSpeed: Long,
        downloadSpeed: Long,
        modifier: Modifier = Modifier
    ) {
        RequestPermissions()
        val context = LocalContext.current

        val locationPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { isGranted ->
            if (!isGranted) {
                Log.e("GPS", "Permission de localisation refusée")
            }
        }

        LaunchedEffect(Unit) {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }

        Column(
            modifier = modifier.padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(text = "Accéléromètre", style = MaterialTheme.typography.headlineSmall)
            Text(text = "X: $accelX m/s²")
            Text(text = "Y: $accelY m/s²")
            Text(text = "Z: $accelZ m/s²")

            Spacer(modifier = Modifier.height(16.dp))

            Text(text = "GPS", style = MaterialTheme.typography.headlineSmall)
            Text(text = "Latitude: $latitude")
            Text(text = "Longitude: $longitude")

            Spacer(modifier = Modifier.height(16.dp))

            Text(text = "Vitesse", style = MaterialTheme.typography.headlineSmall)
            Text(text = "Vitesse: ${"%.2f".format(vitesse)} km/h")

            Spacer(modifier = Modifier.height(16.dp))

            Text(text = "Humidité et Température", style = MaterialTheme.typography.headlineSmall)
            Text(text = "Humidité relative: ${"%.2f".format(humidity)} %")
            Text(text = "Température ambiante: ${"%.2f".format(temperature)} °C")

            Spacer(modifier = Modifier.height(16.dp))

            Text(text = "Wi-Fi", style = MaterialTheme.typography.headlineSmall)
            Text(text = "SSID: $wifiSSID")
            Text(text = "Signal: $wifiSignalStrength dBm")

            Spacer(modifier = Modifier.height(16.dp))

            Text(text = "Réseau", style = MaterialTheme.typography.headlineSmall)
            Text(text = "Upload: $uploadSpeed KB")
            Text(text = "Download: $downloadSpeed KB")

            Button(onClick = { sauvegarderCSV() }) {
                Text(text = "Télécharger CSV")
            }

        }
    }

    @Composable
    fun RequestPermissions() {
        val context = LocalContext.current
        val locationPermissionLauncher = rememberLauncherForActivityResult(
            ActivityResultContracts.RequestPermission()
        ) { isGranted ->
            if (!isGranted) {
                Log.e("WiFi", "Permission de localisation refusée. Impossible d'afficher l'SSID.")
            }
        }

        LaunchedEffect(Unit) {
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }
    }

    @Preview(showBackground = true)
    @Composable
    fun DataScreenPreview() {
        Info0806ProjetTheme {
            DataScreen(
                accelX = 0f,
                accelY = 0f,
                accelZ = 0f,
                latitude = 48.8566,
                longitude = 2.3522,
                vitesse = 10.5,
                humidity = 60f,
                temperature = 22.5F,
                wifiSSID = "Exemple_WiFi",
                wifiSignalStrength = -50,
                uploadSpeed = 1024, // 1 Mo
                downloadSpeed = 2048 // 2 Mo
            )
        }
    }
}