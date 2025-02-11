#!/usr/bin/env python3
import time
import subprocess
from pydbus import SystemBus
from evdev import InputDevice, list_devices

def find_keyboard_device_name():
    """
    Sucht in /dev/input/event*-Geräten nach einem Gerät, dessen Name auf eine interne Tastatur hindeutet.
    Rückgabe: Der Gerätename als String (z. B. "AT Translated Set 2 keyboard"), der für den hyprctl-Befehl genutzt wird.
    Passe den Filter ggf. an, falls dein Gerät einen anderen Namen hat.
    """
    for dev_path in list_devices():
        try:
            dev = InputDevice(dev_path)
            name_lower = dev.name.lower()
            if "keyboard" in name_lower or "at translated" in name_lower:
                print(f"Gefundene Tastatur: {dev.name} ({dev_path})")
                return dev.name
        except Exception:
            continue
    return None

def disable_internal_keyboard(keyboard_name):
    """
    Deaktiviert die interne Tastatur über hyprctl.
    Erwarteter Befehl (Beispiel): 
      hyprctl keyword input "AT Translated Set 2 keyboard,disable,1"
    Passe diesen Befehl an deine Gegebenheiten an, falls nötig.
    """
    print(f"Deaktiviere interne Tastatur: {keyboard_name}")
    subprocess.call(["hyprctl", "keyword", "input", f"{keyboard_name},disable,1"])

def enable_internal_keyboard(keyboard_name):
    """
    Aktiviert die interne Tastatur über hyprctl.
    Erwarteter Befehl (Beispiel): 
      hyprctl keyword input "AT Translated Set 2 keyboard,disable,0"
    """
    print(f"Aktiviere interne Tastatur: {keyboard_name}")
    subprocess.call(["hyprctl", "keyword", "input", f"{keyboard_name},disable,0"])

def rotate_display(rotation):
    """
    Dreht das Display über hyprctl.
    Parameter rotation sollte "normal" oder "180" sein.
    Der Befehl setzt per Beispiel:
      hyprctl keyword monitor "eDP-1,transform,180"
    Passe 'monitor_name' an dein Setup an.
    """
    monitor_name = "eDP-1"  # Anpassen, falls nötig
    print(f"Setze Displayrotation auf {rotation}°")
    subprocess.call(["hyprctl", "keyword", "monitor", f"{monitor_name},transform,{rotation}"])

def main():
    # Verbindung zum Systembus und iio-sensor-proxy herstellen
    bus = SystemBus()
    try:
        sensor_proxy = bus.get("net.hadess.SensorProxy", "/net/hadess/SensorProxy")
    except Exception as e:
        print("Fehler beim Verbinden mit iio-sensor-proxy:", e)
        return

    # Ermittele den Namen der internen Tastatur
    keyboard_name = find_keyboard_device_name()
    if not keyboard_name:
        print("Interne Tastatur nicht gefunden!")
        return

    keyboard_disabled = False
    current_rotation = "normal"  # Ausgangszustand des Displays
    last_orientation = None

    print("Starte Sensorüberwachung. Drücke STRG+C zum Beenden.")
    try:
        while True:
            try:
                # Lese die aktuelle Orientierung (z. B. "normal" oder "bottom-up")
                orientation = sensor_proxy.AccelerometerOrientation
            except Exception as e:
                print("Fehler beim Abrufen der Orientierung:", e)
                time.sleep(1)
                continue

            if orientation != last_orientation:
                print("Ausrichtung geändert:", orientation)
                last_orientation = orientation

            if orientation == "bottom-up":
                # Tabletmodus: Interne Tastatur deaktivieren und Display um 180° drehen
                if not keyboard_disabled:
                    disable_internal_keyboard(keyboard_name)
                    keyboard_disabled = True
                if current_rotation != "180":
                    rotate_display("180")
                    current_rotation = "180"
            else:
                # Anderer Modus (z. B. Laptopmodus): Tastatur aktivieren und Display zurücksetzen
                if keyboard_disabled:
                    enable_internal_keyboard(keyboard_name)
                    keyboard_disabled = False
                if current_rotation != "normal":
                    rotate_display("normal")
                    current_rotation = "normal"

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Beende das Skript...")
        if keyboard_disabled:
            enable_internal_keyboard(keyboard_name)
        if current_rotation != "normal":
            rotate_display("normal")

if __name__ == '__main__':
    main()