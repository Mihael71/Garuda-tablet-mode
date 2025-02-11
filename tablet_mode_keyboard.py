#!/usr/bin/env python3
import time
from pydbus import SystemBus
from evdev import InputDevice, list_devices

def find_keyboard_device():
    """
    Sucht in den /dev/input/event*-Geräten nach einem, dessen Name
    auf eine interne Tastatur hindeutet (z. B. enthält "keyboard" oder "at translated").
    """
    for dev_path in list_devices():
        try:
            dev = InputDevice(dev_path)
            name_lower = dev.name.lower()
            if "keyboard" in name_lower or "at translated" in name_lower:
                print(f"Gefundene Tastatur: {dev.name} ({dev_path})")
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

    # Interne Tastatur suchen
    keyboard_dev = find_keyboard_device()
    if not keyboard_dev:
        print("Interne Tastatur nicht gefunden!")
        return

    keyboard_disabled = False
    last_orientation = None

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

            # Wenn die Ausrichtung "bottom-up" ist, interpretieren wir das als Tabletmodus
            if orientation == "bottom-up":
                if not keyboard_disabled:
                    try:
                        keyboard_dev.grab()  # Tastatur blockieren
                        keyboard_disabled = True
                        print("Tastatur deaktiviert (Tabletmodus).")
                    except Exception as e:
                        print("Fehler beim Deaktivieren der Tastatur:", e)
            else:
                if keyboard_disabled:
                    try:
                        keyboard_dev.ungrab()  # Tastatur wieder freigeben
                        keyboard_disabled = False
                        print("Tastatur aktiviert (Laptopmodus).")
                    except Exception as e:
                        print("Fehler beim Aktivieren der Tastatur:", e)

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Beende das Skript...")
        if keyboard_disabled:
            try:
                keyboard_dev.ungrab()
                print("Tastatur wieder aktiviert.")
            except Exception as e:
                print("Fehler beim Freigeben der Tastatur:", e)

if __name__ == '__main__':
    main()
