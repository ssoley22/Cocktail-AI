from arduino import CocktailMachine, ArduinoError


def main():
    print("Connectant amb Arduino...")

    try:
        machine = CocktailMachine(port="/dev/ttyUSB0")
        print("Arduino connectat i HOME inicial correcte.")
    except Exception as e:
        print(f"Error connectant amb Arduino: {e}")
        return

    print()
    print("Ordres disponibles:")
    print("  HOME")
    print("  A1 3300")
    print("  A2 3300")
    print("  A3 3300")
    print("  A4 3300")
    print("  A5 3300")
    print("  A6 3300")
    print("  ICE 600")
    print("  EXIT")
    print()

    while True:
        command = input("Ordre > ").strip().upper()

        if command == "EXIT":
            break

        if not command:
            continue

        try:
            if command == "HOME":
                machine.home()
                print("Resposta: HOME OK")

            elif command.startswith("A"):
                parts = command.split()
                bottle = int(parts[0][1])
                ms = int(parts[1]) if len(parts) > 1 else 3300

                machine.dispense_bottle(bottle, ms)
                print("Resposta: OK")

            elif command.startswith("ICE"):
                parts = command.split()
                ms = int(parts[1]) if len(parts) > 1 else 600

                machine.dispense_ice(ms)
                print("Resposta: ICE OK")

            else:
                print("Ordre no reconeguda.")

        except ArduinoError as e:
            print(f"Error Arduino: {e}")

        except Exception as e:
            print(f"Error: {e}")

    machine.close()
    print("Connexió tancada.")


if __name__ == "__main__":
    main()