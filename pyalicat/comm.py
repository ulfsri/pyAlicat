"""
Sets up the communication for the Alicat device.

Author: Grayson Bellamy
Date: 2024-01-05
"""

import trio
from trio_serial import SerialStream
from trio_serial import Parity, StopBits
from abc import ABC, abstractmethod
from typing import Optional, ByteString


class CommDevice(ABC):
    """
    Sets up the communication for the an Alicat device.
    """

    def __init__(self, timeout: int) -> None:
        """
        Initializes the serial communication.

        Parameters
        ----------
        timeout : int
            The timeout of the Alicat device.
        """

        self.timeout = timeout

    @abstractmethod
    async def _read(self, len: int) -> Optional[str]:
        """
        Reads the serial communication.

        Returns
        -------
        str
            The serial communication.
        """
        pass

    @abstractmethod
    async def _write(self, command: str) -> None:
        """
        Writes the serial communication.

        Parameters
        ----------
        command : str
            The serial communication.
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Closes the serial communication.
        """
        pass

    @abstractmethod
    async def _readline(self) -> Optional[str]:
        """
        Reads the serial communication until end-of-line character reached

        Returns
        -------
        str
            The serial communication.
        """
        pass

    @abstractmethod
    async def _write_readline(self, command: str) -> Optional[str]:
        """
        Writes the serial communication and reads the response until end-of-line character reached

        Parameters:
            command (str):
                The serial communication.

        Returns:
            str: The serial communication.
        """
        pass


class SerialDevice(CommDevice):
    """
    Sets up the communication for the an Alicat device using serial protocol.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: int = 150,
        databits: int = 8,
        parity: Parity = Parity.NONE,
        stopbits: StopBits = StopBits.ONE,
        xonxoff: bool = False,
        rtscts: bool = False,
        exclusive: bool = False,
    ):
        """
        Initializes the serial communication.

        Parameters
        ----------
        port : str
            The port to which the Alicat device is connected.
        baudrate : int
            The baudrate of the Alicat device.
        timeout : int
            The timeout of the Alicat device in ms.
        """
        super().__init__(timeout)

        self.timeout = timeout
        self.eol = b"\r"
        self.serial_setup = {
            "port": port,
            "exclusive": exclusive,
            "baudrate": baudrate,
            "bytesize": databits,
            "parity": parity,
            "stopbits": stopbits,
            "xonxoff": xonxoff,
            "rtscts": rtscts,
        }
        self.ser_devc = SerialStream(**self.serial_setup)

    async def _read(self, len: int = 1) -> ByteString:
        """
        Reads the serial communication.

        Returns
        -------
        ByteString
            The serial communication.
        """
        return await self.ser_devc.receive_some(len)

    async def _write(self, command: str) -> None:
        """
        Writes the serial communication.

        Parameters
        ----------
        command : str
            The serial communication.
        """
        with trio.move_on_after(self.timeout / 1000):
            await self.ser_devc.send_all(command.encode("ascii") + self.eol)

    async def _readline(self) -> str:
        """
        Reads the serial communication until end-of-line character reached

        Returns
        -------
        str
            The serial communication.
        """
        async with self.ser_devc:
            line = bytearray()
            while True:
                with trio.move_on_after(self.timeout / 1000):
                    c = await self._read(1)
                    line += c
                    if c == self.eol:
                        break
        return line.decode("ascii")

    async def _write_readall(self, command: str) -> list:
        """
        Write command and read until timeout reached.

        Returns
        -------
        str
            The serial communication.
        """
        async with self.ser_devc:
            await self._write(command)
            line = bytearray()
            arr_line = []
            while True:
                c = None
                with trio.move_on_after(self.timeout / 1000):
                    c = await self._read(1)
                    if c == self.eol:
                        arr_line.append(line.decode("ascii"))
                        line = bytearray()
                    else:
                        line += c
                if c is None:
                    break
        return arr_line

    async def _write_readline(self, command: str) -> str:
        """
        Writes the serial communication and reads the response until end-of-line character reached

        Parameters:
            command (str):
                The serial communication.

        Returns:
            str: The serial communication.
        """
        async with self.ser_devc:
            await self._write(command)
            line = bytearray()
            while True:
                with trio.move_on_after(self.timeout / 1000):
                    c = await self._read(1)
                    if c == self.eol:
                        break
                    line += c
            return line.decode("ascii")

    async def _flush(self) -> None:
        """
        Flushes the serial communication.
        """
        await self.ser_devc.discard_input()

    async def close(self) -> None:
        """
        Closes the serial communication.
        """
        await self.ser_devc.aclose()

    async def open(self) -> None:
        """
        Opens the serial communication.
        """
        await self.ser_devc.aopen()
