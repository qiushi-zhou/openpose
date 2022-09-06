import datetime

import socketio
import time
import asyncio
import threading

class Status:
    def __init__(self, _id, name, description):
        self.id = _id
        self.name = name
        self.description = description
        self.extra = ''

    def get_dbg_text(self, ws):
        synced = "(SYNCD)" if ws.sync_with_server else ""
        return f"{synced} {self.name}: {self.description}"


class Statuses:
    pass


async def send_test(dict_data, namespace):
    global ws
    print(f"Sending test!")
    await ws.sio.emit(event='frame_data_in', data=dict_data, namespace=namespace)

Statuses.NOT_INITIALIZED = Status(-1, "NOT INITIALIZED", "Socket.io created but not initialized")
Statuses.INITIALIZED = Status(0, "INITIALIZED", "Socket.io setup but not connected")
Statuses.CONNECTING = Status(1, "CONNECTING", "Socket.io is trying to connect")
Statuses.CONNECTED = Status(2, "CONNECTED", "Socket.io connected")
Statuses.WAITING = Status(3, "WAITING", "Socket.io connected")
Statuses.DISCONNECTED = Status(4, "DISCONNECTED", "Socket.io lost connection")

# sio = socketio.Client()

# @sio.event(namespace='/visualization')
async def connect():
    global ws
    print(f"Connected")
    ws.set_status(Statuses.CONNECTED, f"{ws.uri}")
    print(f"Sending ping")
    await ws.sio.emit(event="ping", data={}, namespace="/visualization")

# @sio.event(namespace='/visualization')
async def connect_error(data):
    global ws
    print(f"CONNECTION ERROR!")
    ws.set_status(Statuses.DISCONNECTED, f"{ws.uri} {data}")


# @sio.event(namespace='/visualization')
async def frame_received(*args):
    global ws
    print(f"elapsed: {(ws.last_emit - datetime.datetime.now()).microseconds / 1000}")
    ws.set_status(Statuses.CONNECTED, f"Frame received", debug=False)


async def scale_request_received(*args):
    global ws
    if len(args) > 0:
        data = args[0]
        ws.set_scaling(float(data.get('scaling_factor', 1.0)))
    # print(f"elapsed: {(ws.last_emit - datetime.datetime.now()).microseconds / 1000}")
    # ws.set_status(Statuses.CONNECTED, f"Frame received", debug=False)


# @sio.event(namespace='/visualization')
async def op_frame_new(*args):
    global ws
    if len(args) > 0:
        data = args[0]
        # print(f"Received op_frame_new from {data}")
    ws.set_status(Statuses.CONNECTED, f"{ws.uri} {data}", debug=False)


# @sio.event(namespace='/visualization')
async def disconnect():
    global ws
    ws.set_status(Statuses.DISCONNECTED, f"{ws.uri}")


# @sio.event(namespace='/visualization')
async def hey(*args):
    global ws
    if len(args) > 0:
        data = args[0]
        print(f"Received msg from {data}")
    ws.set_status(Statuses.CONNECTED, f"{ws.uri} {data}")


class WebSocket:
    def __init__(self, async_loop=None):
        sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.sio = sio
        self.loop = async_loop
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
        self.sync_with_server = False
        self.max_wait_timeout = 10
        self.wait_time = 0
        self.tag = "WebSocket"
        self.status = Statuses.NOT_INITIALIZED
        self.url = ""
        self.namespace = ""
        self.last_emit = datetime.datetime.now()
        self.uri = self.url + self.namespace
        self.scaling_factor = 1.0

    def set_async_loop(self, loop):
        self.loop = loop

    def init(self):
        self.set_status(Statuses.DISCONNECTED, {self.uri})
        self.attach_callbacks()
        self.update_status()
        self.send_msg()

    def attach_callbacks(self):
        self.sio.on('connect', handler=connect, namespace=self.namespace)
        self.sio.on('connect_error', handler=connect_error, namespace=self.namespace)
        self.sio.on('hey', handler=hey, namespace=self.namespace)
        self.sio.on('frame_received', handler=frame_received, namespace=self.namespace)
        self.sio.on('scale_request', handler=scale_request_received, namespace=self.namespace)
        self.sio.on('op_frame_new', handler=op_frame_new, namespace=self.namespace)
        self.sio.on('disconnect', handler=disconnect, namespace=self.namespace)

    def set_scaling(self, scaling_factor):
        self.scaling_factor = scaling_factor

    def set_status(self, new_status, extra, debug=True):
        if debug:
            print(f"{self.tag} {self.status.name} -> {new_status.name}, {extra}")
        self.status = new_status
        self.status.extra = extra

    def update_config(self, data):
        self.sync_with_server = data.get("sync_with_server", False)
        url = data.get("url", self.url)
        recreate = url != self.url
        namespace = data.get("namespace", self.namespace)
        recreate = recreate or namespace != self.namespace
        if recreate:
            print(f"WebSocket URI changed from {self.url}{self.namespace} to {url}{namespace}, reconnecting")
            self.url = url
            self.namespace = namespace
            self.uri = url + namespace
            self.init()

    def update_status(self):
        if self.sio.connected:
            if self.status.id == Statuses.WAITING.id:
                elapsed = time.time() - self.wait_time
                if elapsed > self.max_wait_timeout:
                    self.wait_time = 0
                    self.set_status(Statuses.CONNECTED, self.uri)
                    return True
                return False
            elif self.status.id != Statuses.CONNECTED.id:
                # Maybe something went wrong and we missed the connected message but socketio still connected somehow!
                self.set_status(Statuses.CONNECTED, self.uri)
            return True
        else:
            if self.status.id == Statuses.CONNECTING.id:
                return False
            elif self.status.id == Statuses.CONNECTED.id:
                self.set_status(Statuses.DISCONNECTED, self.uri)
                return False
            elif self.status.id in [Statuses.DISCONNECTED.id, Statuses.NOT_INITIALIZED.id]:
                self.set_status(Statuses.CONNECTING, self.uri)

                self.loop.run_until_complete(self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1))
                # self.sio.connect(self.url, namespaces=[self.namespace], wait_timeout=1)
                # time.sleep(1) # Otherwise it might get stuck in a loop as the status will change to connected WHILE it was in the "sio.connected" else
                return False
            else:
                self.set_status(Statuses.DISCONNECTED, self.uri)
            return False

    def is_ready(self):
        return self.status.id == Statuses.CONNECTED.id

    def send_msg(self, msg="test_msg"):
        self.loop.run_until_complete(self.sio.emit(event=msg, namespace=self.namespace))
        # self.sio.emit(event='test_msg', namespace=self.namespace)

    async def send_msg_async(self):
        print(f"Sending msg websocket")
        await self.sio.emit(event='test_msg', namespace=self.namespace, callback=frame_received)
        # self.sio.emit(event='test_msg', namespace=self.namespace)

    def start_async_task(self, dict_data):
        global ws
        self.sio.start_background_task(ws.sio.emit, event='frame_data_in', data=dict_data, namespace=self.namespace)

    async def send_image_data(self, dict_data):
        # if self.status.id != Statuses.CONNECTED.id:
        #     return False
        try:
            if self.sync_with_server:
                self.set_status(Statuses.WAITING, "Send_data", debug=False)
                self.last_emit = datetime.datetime.now()
                await self.sio.emit(event='gallery_stream', data=dict_data, namespace=self.namespace, callback=frame_received)
            else:
                print(f"Emitting 'gallery_stream' on {self.namespace} from Thread ws: {threading.current_thread().getName() }")
                # print(dict_data)
                await self.sio.emit(event='gallery_stream', data=dict_data, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending frame data to WebSocket {e}")
            self.set_status(Statuses.DISCONNECTED, f"{e}")
        return True

    async def send_graph_data(self, data):
        # if self.status.id != Statuses.CONNECTED.id:
        #     return False
        try:
            await self.sio.emit(event='graph_data', data=data, namespace=self.namespace)
        except Exception as e:
            print(f"Error Sending graph data to WebSocket {e}")
            self.set_status(Statuses.DISCONNECTED, f"{e}")
        return True

ws = WebSocket()
