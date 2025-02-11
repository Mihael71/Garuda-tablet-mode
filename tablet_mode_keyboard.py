#!/usr/bin/env python3
import time
import subprocess
from pydbus import SystemBus
from evdev import InputDevice, list_devices

def find_keyboard_device():
    """
    Sucht in den /dev/input/event*-Geräten nach einem, dessen Name
    auf eine interne Tastatur hindeutet (z. B. enthält "keyboard" oder "at translated").
    Passe den Filter ggf. an dein Gerät an!
    """
    for dev_path in list_devices():
        try:
            dev = InputDevice(dev_path)
            name_lower = dev.name.lower()
            if "keyboard" in name_lower or "at translated" in name_lower:
                print(f"Gefundene physische Tastatur: {dev.name} ({dev_path})")
                return dev
        except Exception as e:
            continue
    return None

def main():
    # Verbindung zum Systembus und zum iio-sensor-proxy herstellen
    bus = SystemBus()
    try:
        sensor_proxy = bus.get("net.hadess.SensorProxy", "/net/hadess/SensorProxy")
    except Exception as e:
        print("Fehler beim Verbinden mit iio-sensor-proxy:", e)
        return

    # Interne (physische) Tastatur suchen
    keyboard_dev = find_keyboard_device()
    if not keyboard_dev:
        print("Physische Tastatur nicht gefunden!")
        return

    keyboard_disabled = False
    last_orientation = None
    vk_process = None  # Hier halten wir den Prozess der virtuellen Tastatur

    print("Starte Sensorüberwachung. Drücke STRG+C zum Beenden.")
    try:
        while True:
            # Lese die aktuelle Ausrichtung vom Accelerometer (über iio-sensor-proxy)
            try:
                orientation = sensor_proxy.AccelerometerOrientation
            except Exception as e:
                print("Fehler beim Abrufen der Orientierung:", e)
                time.sleep(1)
                continue

            if orientation != last_orientation:
                print("Ausrichtung geändert:", orientation)
                last_orientation = orientation

            # Wenn die Orientierung "bottom-up" ist, interpretieren wir das als Tabletmodus
            if orientation == "bottom-up":
                # Physische Tastatur deaktivieren
                if not keyboard_disabled:
                    try:
                        keyboard_dev.grab()  # Blockiert die physische Tastatur
                        keyboard_disabled = True
                        print("Physische Tastatur deaktiviert (Tabletmodus).")
                    except Exception as e:
                        print("Fehler beim Deaktivieren der Tastatur:", e)
                # Virtuelle Tastatur starten, falls noch nicht geschehen
                if vk_process is None:
                    try:
                        vk_process = subprocess.Popen(["maliit-keyboard"])
                        print("Virtuelle Tastatur gestartet.")
                    except Exception as e:
                        print("Fehler beim Starten der virtuellen Tastatur:", e)
            else:
                # Tabletmodus ist nicht aktiv – also physische Tastatur freigeben
                if keyboard_disabled:
                    try:
                        keyboard_dev.ungrab()
                        keyboard_disabled = False
                        print("Physische Tastatur aktiviert (Laptopmodus).")
                    except Exception as e:
                        print("Fehler beim Aktivieren der Tastatur:", e)
                # Virtuelle Tastatur beenden, falls sie läuft
                if vk_process is not None:
                    try:
                        vk_process.terminate()
                        vk_process.wait(timeout=5)
                        print("Virtuelle Tastatur beendet.")
                    except Exception as e:
                        print("Fehler beim Beenden der virtuellen Tastatur:", e)
                    vk_process = None

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Beende das Skript...")
        if keyboard_disabled:
            try:
                keyboard_dev.ungrab()
                print("Physische Tastatur wieder aktiviert.")
            except Exception as e:
                print("Fehler beim Freigeben der Tastatur:", e)
        if vk_process is not None:
            try:
                vk_process.terminate()
                vk_process.wait(timeout=5)
                print("Virtuelle Tastatur beendet.")
            except Exception as e:
                print("Fehler beim Beenden der virtuellen Tastatur:", e)

if __name__ == '__main__':
    main()
