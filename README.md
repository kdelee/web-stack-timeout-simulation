# Webserver Timeout Simulation

This python script simulates a stack of proxies/webservers that each have their own timeouts and latencies.
The user provides average latency of each layer and the timeout configured.
The simulation uses log normal distribution to determine latency of any single request.


## Install
```
pip install --user numpy matplotlib
```

## Run

```
python simulate_timeouts.py
```

Either answer prompts for various configuraitons or press enter to use the default.
The result is a graph showing histogram of the request latencies given the specified configuraiton.

## Interperet
This is an exteremly simplified model of real web server/proxy stack. But it gives rough idea of
what can happen when timeouts/latencies are mismatched.