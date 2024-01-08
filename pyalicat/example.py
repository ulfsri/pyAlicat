"""Example of code."""
import trio
import timeit
from trio import run
from trio_serial import SerialStream

eol = b'\r'
async def main():
    async with SerialStream('/dev/ttyUSB0', baudrate=115200) as ser:
        buf = ('A??M*').encode() + eol
        await ser.send_all(buf)
        line = bytearray()
        i = 0
        while True:
            c = await ser.receive_some(1)
            line += c
            i += 1
            if c == eol:
                print(i)
                break
        return line
    
# Time the execution of the main function
start_time = timeit.default_timer()
print(run(main))
end_time = timeit.default_timer()

print(f"Execution time: {(end_time - start_time)*1000} milliseconds")