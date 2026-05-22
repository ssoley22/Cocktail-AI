import serial
import time
import threading


class ArduinoError(Exception):
    pass


class CocktailMachine:
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, timeout=2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.lock = threading.Lock()
        self.serial = None

        self.connect()

    def connect(self):
        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout
        )

        # Quan s'obre el port sèrie, l'Arduino normalment es reinicia
        time.sleep(2)

        self.wait_startup_home()

    def wait_startup_home(self):
        start = time.time()
        max_wait = 30

        while time.time() - start < max_wait:
            line = self.read_line()

            if line == "HOME OK":
                return

            if line == "ERR":
                raise ArduinoError("Arduino ha fallat fent HOME inicial.")

        raise ArduinoError("Timeout esperant HOME OK inicial de l'Arduino.")

    def read_line(self):
        if self.serial is None:
            raise ArduinoError("Arduino no connectat.")

        line = self.serial.readline()
        return line.decode("utf-8", errors="ignore").strip()

    def send_command_sync(self, command, expected_responses=None, timeout=30):
        if expected_responses is None:
            expected_responses = ["OK"]

        with self.lock:
            if self.serial is None:
                raise ArduinoError("Arduino no connectat.")

            full_command = command.strip() + "\n"
            self.serial.write(full_command.encode("utf-8"))
            self.serial.flush()

            start = time.time()

            while time.time() - start < timeout:
                line = self.read_line()

                if not line:
                    continue

                if line in expected_responses:
                    return True

                if line == "ERR":
                    raise ArduinoError(f"L'Arduino ha retornat ERR amb ordre: {command}")

            raise ArduinoError(f"Timeout esperant resposta de l'Arduino amb ordre: {command}")

    def home(self):
        return self.send_command_sync(
            "HOME",
            expected_responses=["HOME OK"],
            timeout=60
        )

    def dispense_bottle(self, bottle, ms=3300):
        if bottle < 1 or bottle > 6:
            raise ValueError("L'ampolla ha d'estar entre 1 i 6.")

        if ms <= 0 or ms > 10000:
            raise ValueError("Temps de dispensació invàlid.")

        command = f"A{bottle} {ms}"
        return self.send_command_sync(
            command,
            expected_responses=["OK"],
            timeout=60
        )

    def dispense_ice(self, ms=600):
        if ms <= 0 or ms > 10000:
            raise ValueError("Temps de gel invàlid.")

        command = f"ICE {ms}"
        return self.send_command_sync(
            command,
            expected_responses=["ICE OK"],
            timeout=60
        )

    def close(self):
        if self.serial is not None:
            self.serial.close()
            self.serial = None