import random
import heapq
import numpy as np

# Parameters
OPENING = 0          # 10:00 mins from 10:00
CLOSING = 660        # 21:00 in mins

# Time intervals (start, end, arrival rate in clients/min)
INTERVALS = [
    (0, 90, 0.2),      # 10:00 - 11:30 (normal)
    (90, 210, 0.5),    # 11:30 - 13:30 (rush)
    (210, 420, 0.2),   # 13:30 - 17:00 (normal)
    (420, 540, 0.5),   # 17:00 - 19:00 (rush)
    (540, CLOSING, 0.2) # 19:00 - 21:00 (normal)
]

# Service parameters
SANDWICH_PROB = 0.5
SANDWICH_TIME_MIN, SANDWICH_TIME_MAX = 3, 5
SUSHI_TIME_MIN, SUSHI_TIME_MAX = 5, 8

WAITING_THRESHOLD = 5.0   # minutes

SEED = 42                # for reproducibility
REPLICAS_NUM = 100

# Arrival generation (non‑homogeneous Poisson)
def generate_arrival_times(intervals):
    """
    Generates a sorted list of client arrival times for a day,
    according to a non‑homogeneous Poisson process.

    Params:
        intervals: list of tuples (start, end, rate)

    Returns:
        list of times (float) in minutes from OPENING
    """
    times = []
    for start, end, rate in intervals:
        duration = end - start
        n_arrivals = np.random.poisson(rate * duration)
        if n_arrivals > 0:
            u = np.random.uniform(start, end, n_arrivals)
            times.extend(u)
    times.sort()
    return times


class Client:
    """Represents a client with arrival time and type."""
    __slots__ = ('arrival', 'type', 'id')
    _ids = 0

    def __init__(self, arrival, type):
        self.arrival = arrival
        self.type = type          # 'sandwich' or 'sushi'
        self.id = Client._ids
        Client._ids += 1


class Simulation:
    """
    Discrete‑event simulation of Kojo's Kitchen.
    Servers are indistinguishable → modelled by a counter.
    """

    def __init__(self, use_extra_rush=False, seed=None):
        """
        Initialises the simulation.

        Params:
            use_extra_rush: bool, if True adds a third employee during rush hours
            seed: int or None, random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.use_extra = use_extra_rush
        self.clock = 0.0

        # Queue of waiting clients
        self.queue = []

        self.total_servers = 2
        self.free_servers = 2
        
        self.service_end_times = [] # Min‑heap of finish times of all ongoing services

        # Metrics
        self.waiting_times = []  
        self.served_clients = 0

        # Event queue: (time, event_type, data)
        # event_type: 'arrival', 'departure', 'staff_change', 'stop'
        self.events = []

        self.arrivals = self._generate_arrivals_with_type()

        # Schedule staff changes if needed
        if self.use_extra:
            self._schedule_event(90.0, 'staff_change', 'add')
            self._schedule_event(210.0, 'staff_change', 'remove')
            self._schedule_event(420.0, 'staff_change', 'add')
            self._schedule_event(540.0, 'staff_change', 'remove')

        # Schedule all arrival events
        for arrival_time, client_type in self.arrivals:
            self._schedule_event(arrival_time, 'arrival', client_type)

        self._schedule_event(CLOSING, 'stop', None)

    # Internal helpers
    def _generate_arrivals_with_type(self):
        """
        Generates arrival times using non‑homogeneous Poisson and assigns
        a random type to each client.
        """
        times = generate_arrival_times(INTERVALS)
        arrivals = []
        for t in times:
            typ = 'sandwich' if random.random() < SANDWICH_PROB else 'sushi'
            arrivals.append((t, typ))
        return arrivals

    def _schedule_event(self, time, event_type, data):
        """Adds an event to the priority queue."""
        heapq.heappush(self.events, (time, event_type, data))


    # Core logic
    def _start_service(self, client, current_time):
        """
        Starts serving a client, assuming at least one server is free.
        Returns True if service started, False if no free server.
        """
        if self.free_servers == 0:
            return False

        self.free_servers -= 1

        # Service duration according to client type
        if client.type == 'sandwich':
            duration = random.uniform(SANDWICH_TIME_MIN, SANDWICH_TIME_MAX)
        else:
            duration = random.uniform(SUSHI_TIME_MIN, SUSHI_TIME_MAX)

        finish_time = current_time + duration
        # Store the finish time in the heap
        heapq.heappush(self.service_end_times, finish_time)
        # Schedule a departure event at this finish time
        self._schedule_event(finish_time, 'departure', None)

        # Record waiting time
        wait = current_time - client.arrival
        self.waiting_times.append(wait)
        self.served_clients += 1

        return True

    def _serve_queue(self):
        """Assigns waiting clients to free servers as long as both exist."""
        while self.queue and self.free_servers > 0:
            client = self.queue.pop(0)
            self._start_service(client, self.clock)

    def _manage_arrival(self, time, client_type):
        """Processes an arrival event."""
        if time >= CLOSING:
            return
        self.clock = time
        client = Client(time, client_type)

        if not self._start_service(client, self.clock):
            # No free server → enqueue
            self.queue.append(client)

    def _manage_departure(self, time, _):
        """
        Processes all departures that have occurred up to 'time'.
        The second argument is ignored (was server_id in old version).
        """
        self.clock = time

        # Release all servers whose service has finished
        while self.service_end_times and self.service_end_times[0] <= time:
            heapq.heappop(self.service_end_times)
            self.free_servers += 1

        # In case a staff removal reduced total_servers, cap free_servers
        if self.free_servers > self.total_servers:
            self.free_servers = self.total_servers

        # Try to serve waiting clients with the newly freed servers
        self._serve_queue()

    def _manage_staff_change(self, time, action):
        """Adds or removes an employee (staff_change event)."""
        self.clock = time
        if action == 'add':
            self.total_servers += 1
            self.free_servers += 1
            self._serve_queue()
        else:  # action == 'remove'
            self.total_servers -= 1

    def _manage_stop(self, time):
        """Ends the simulation."""
        self.clock = time

    # Main simulation loop
    def run(self):
        """Executes the simulation until all events are processed."""
        while self.events:
            time, event_type, data = heapq.heappop(self.events)
            if time > CLOSING:
                continue
            if event_type == 'arrival':
                self._manage_arrival(time, data)
            elif event_type == 'departure':
                self._manage_departure(time, data)
            elif event_type == 'staff_change':
                self._manage_staff_change(time, data)
            elif event_type == 'stop':
                self._manage_stop(time)
                break

    def get_waiting_percentage(self):
        """
        Returns the percentage of clients whose waiting time exceeded the threshold.
        """
        if not self.waiting_times:
            return 0.0
        n_exceed = sum(1 for w in self.waiting_times if w > WAITING_THRESHOLD)
        return 100.0 * n_exceed / len(self.waiting_times)


# Multiple replicas
def simulate_replicas(use_extra_rush, num_replicas=REPLICAS_NUM, base_seed=SEED):
    """
    Runs several independent replicas and returns the average percentage
    of clients waiting longer than WAITING_THRESHOLD and its standard deviation.
    """
    percentages = []
    for r in range(num_replicas):
        sim = Simulation(use_extra_rush=use_extra_rush, seed=base_seed + r)
        sim.run()
        pct = sim.get_waiting_percentage()
        percentages.append(pct)

    mean = np.mean(percentages)
    std = np.std(percentages)
    return mean, std


# Main execution
if __name__ == "__main__":
    print("Kojo's Kitchen Simulation")
    print(f"Params: normal rate = {INTERVALS[0][2]} cli/min, rush rate = {INTERVALS[1][2]} cli/min")
    print(f"Waiting threshold = {WAITING_THRESHOLD} minutes")
    print(f"Number of replicas = {REPLICAS_NUM}\n")

    mean2, std2 = simulate_replicas(use_extra_rush=False)
    print("Current Scenario (2 fixed employees):")
    print(f"Percentage of clients waiting > {WAITING_THRESHOLD} min = {mean2:.2f}% ± {std2:.2f}%")

    mean3, std3 = simulate_replicas(use_extra_rush=True)
    print("\nAlternative scenario (3 employees during rush hours):")
    print(f"Percentage of clients waiting > {WAITING_THRESHOLD} min = {mean3:.2f}% ± {std3:.2f}%")