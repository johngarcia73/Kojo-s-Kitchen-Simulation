import random
import heapq
import numpy as np
from collections import namedtuple

# Parameters
OPENING = 0          # 10:00 mins from 10:00
CLOSING = 660          # 21:00 in mins

# Time slaps (start, end, arrivals rate as clients/min)
INTERVALS = [
    (0, 90, 0.2),      # 10:00 - 11:30 (normal)
    (90, 210, 0.5),    # 11:30 - 13:30 (rush)
    (210, 420, 0.2),   # 13:30 - 17:00 (normal)
    (420, 540, 0.5),   # 17:00 - 19:00 (rush)
    (540, CLOSING, 0.2) # 19:00 - 21:00 (normal)
]

# Service params
SANDWICH_PROB = 0.5
SANDWICH_TIME, MAX_SANDWICH_TIME = 3, 5
SUSHI_TIME, MAX_SUSHI_TIME = 5, 8

WAITING_THRESHOLD = 5.0

SEED = 42  # for reproducibility

REPLICAS_NUM = 1000

# Arivals generation (non-homogeneus Poisson) ----------
def generate_arrival_times(intervals):
    """
    Generates a sorted client arrival times list for a day, accordig to
    a non-homogeneus Poisson process

    Params:
        intervals: tulpes list (start, end, rate)
    Returns: 
        times list in minutes since OPENING
    """
   
    times = []
    for start, end, rate in intervals:
        duration = end - start
        # Arrivals number ~ Poisson(rate * duración)
        n_arrivals = np.random.poisson(rate * duration)
        # Generate uniform positions
        if n_arrivals > 0:
            u = np.random.uniform(start, end, n_arrivals)
            times.extend(u)
    times.sort()
    return times


class Client:
    """Represents a client with it's arrival time and type."""
    __slots__ = ('arrival', 'type', 'id')
    _ids = 0

    def __init__(self, arrival, type):
        self.arrival = arrival
        self.type = type
        self.id = Client._ids
        Client._ids += 1

# Server
class Server:
    """Represents an employee who can prepare both menus"""
    __slots__ = ('active', 'occupied_until', 'id')
    _ids = 0

    def __init__(self, active=True):
        self.active = active      # If is available for new tasks
        self.occupied_until = None # Current service's end time
        self.id = Server._ids
        Server._ids += 1

    @property
    def free(self):
        return self.occupied_until is None

    def occupy(self, duration, current_time):
        """Assigns a task to server."""
        self.occupied_until = current_time + duration

    def liberate(self):
        """Frees server after finish"""
        self.occupied_until = None

# Simulation
class Simulation:
    """
    Simulation class
    """

    def __init__(self, use_extra_rush=False, SEED=None):
        """
        Initializes simulation

        Params:
            use_extra_rush: bool, if it's true, it adds a new employee
                             during rush whiles.
            SEED: int or None, SEED random generator.
        """
        if SEED is not None:
            random.seed(SEED)
            np.random.seed(SEED)

        self.use_extra = use_extra_rush
        self.clock = 0.0
        self.queue = []               
        self.Servers = []          
        self.waiting_times = []
        self.served_clients = 0

        # Events queue: (time, event_type, data)
        # event_type: 'arrival', 'departure', 'staff_change'
        self.eventos = []
        self.arrivals = self._generar_arrivals_with_type()

        # Initial servers
        for _ in range(2):
            self.Servers.append(Server(active=True))

        if self.use_extra:
            # Staff changes
            self._program_event(90.0, 'staff_change', 'add')
            self._program_event(210.0, 'staff_change', 'remove')
            self._program_event(420.0, 'staff_change', 'add')
            self._program_event(540.0, 'staff_change', 'remove')

        # Arrival events
        for arrival, type in self.arrivals:
            self._program_event(arrival, 'arrival', type)

        # Simulation end
        self._program_event(CLOSING, 'stop')

    def _generar_arrivals_with_type(self):

        """
        Generates arrival times using non-homogeneus Poisson and assigns 
        a random type to each clinet
        """

        times = generate_arrival_times(INTERVALS)
        arrivals = []
        for t in times:
            type = 'sandwich' if random.random() < SANDWICH_PROB else 'sushi'
            arrivals.append((t, type))
        return arrivals

    def _program_event(self, time, type, *datos):
        """Adds a new event to the heap"""
        heapq.heappush(self.eventos, (time, type, datos))

    def _Server_free_active(self):
        """Returns the first active and free server, or None"""
        for s in self.Servers:
            if s.active and s.free:
                return s
        return None

    def _assign_server(self, cliente):
        """Assigns a free server to a client,starts service and schedules exit."""
        serv = self._Server_free_active()
        if serv is None:
            return False

        if cliente.type == 'sandwich':
            duration = random.uniform(SANDWICH_TIME, MAX_SANDWICH_TIME)
        else:
            duration = random.uniform(SUSHI_TIME, MAX_SUSHI_TIME)

        wait = self.clock - cliente.arrival
        self.waiting_times.append(wait)
        self.served_clients += 1

        # Occupies server and schedule exit
        serv.occupy(duration, self.clock)
        self._program_event(serv.occupied_until, 'departure', serv.id)
        return True

    def _serve_queue(self):
        """Tries to assign clients to free servers queue."""
        while self.queue and self._Server_free_active():
            cliente = self.queue.pop(0)
            self._assign_server(cliente)

    def _manage_arrival(self, time, client_type):
        """Process a client arrival."""
        if time >= CLOSING:
            return

        self.clock = time
        client = Client(time, client_type)

        if not self._assign_server(client):
            # No free server, enqueue
            self.queue.append(client)

    def _manage_departure(self, time, server_id):
        """Process client exit"""
        self.clock = time

        # Localizes corresponding server
        Server = None
        for s in self.Servers:
            if s.id == server_id:
                Server = s
                break

        if Server is None:
            return

        Server.liberate()

        if not Server.active:
            self.Servers.remove(Server)
        else:
            self._serve_queue()

    def _manage_staff_changes(self, time, action):
        """
        Adds or removes an employee
        action: 'add' o 'remove'
        """
        self.clock = time
        if action == 'add':
            nuevo = Server(active=True)
            self.Servers.append(nuevo)
            self._serve_queue()
        else:  # accion == 'remove'
            removed = False
            for s in self.Servers:
                if s.active and s.free:
                    self.Servers.remove(s)
                    removed = True
                    break
            if not removed:
                for s in self.Servers:
                    if s.active:
                        s.active = False
                        break

    def _manage_stop(self, time):
        """Nothing, just stops the loop"""
        self.clock = time

    def execute(self):
        """Run simulation until events are spent"""
        while self.eventos:
            time, type, data = heapq.heappop(self.eventos)
            if time > CLOSING:
                continue
            if type == 'arrival':
                self._manage_arrival(time, data[0])
            elif type == 'departure':
                self._manage_departure(time, data[0])
            elif type == 'staff_change':
                self._manage_staff_changes(time, data[0])
            elif type == 'stop':
                self._manage_stop(time)
                break

    def get_waiting_percent(self):
        """
        Computes the clients percetage who waited more than WAITING_THRESHOLD.
        """
        if not self.waiting_times:
            return 0.0
        n_mas = sum(1 for w in self.waiting_times if w > WAITING_THRESHOLD)
        return 100.0 * n_mas / len(self.waiting_times)

# Multiple replicas main simulation function
def simulate_replicas(use_extra_rush, REPLICAS_NUM=REPLICAS_NUM, SEED_base=SEED):
    """
    Performs multiple simulation tries and returns statistics about
    the > 5 minutes waiting percentage.

    Params:
        use_extra_rush: bool
        REPLICAS_NUM: int
        SEED_base: int

    Returns:
        (average, standard_deviation)
    """
    porcentages = []
    for r in range(REPLICAS_NUM):
        SEED = SEED_base + r
        sim = Simulation(use_extra_rush=use_extra_rush, SEED=SEED)
        sim.execute()
        pct = sim.get_waiting_percent()
        porcentages.append(pct)
    average = np.mean(porcentages)
    std = np.std(porcentages)
    return average, std

# Execution
if __name__ == "__main__":
    print("Kojo's Kitchen Simulation'")
    print(f"Params: normal rate = {INTERVALS[0][2]} cli/min, rush rate = {INTERVALS[1][2]} cli/min")
    print(f"Waiting threshold = {WAITING_THRESHOLD} minutes")
    print(f"Tries number = {REPLICAS_NUM}\n")

    prom2, std2 = simulate_replicas(use_extra_rush=False)
    print(f"Current Scenario (2 fixed employees):")
    print(f"Porcentage of clients waiting > {WAITING_THRESHOLD} min = {prom2:.2f}% ± {std2:.2f}%")

    prom3, std3 = simulate_replicas(use_extra_rush=True)
    print(f"\nAlternative scenario(3 employees at rush hour):")
    print(f"Porcentage of clients waiting > {WAITING_THRESHOLD} min = {prom3:.2f}% ± {std3:.2f}%")