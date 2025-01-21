import numpy as np
import matplotlib.pyplot as plt
import sys
import random


# Function to calculate mu and sigma for a log-normal distribution given the average
def calculate_mu_sigma(avg_latency):
    sigma = 0.5 # reasonable stdev, 99.9% of requests of 1 second latency would be served within 8 seconds 
    mu = np.log(avg_latency) - (sigma**2 / 2)
    return mu, sigma


# Function to simulate latency for each layer using log-normal distribution
def simulate_latency_log_normal(avg_latency, timeout):
    mu, sigma = calculate_mu_sigma(avg_latency)
    latency = np.random.lognormal(mu, sigma)
    return min(latency, timeout)


# Function to simulate the full request process
def simulate_request(timeouts, avg_latencies, layer_backlogs):
    # Start from the web server and accumulate latency backwards
    cumulative_latency = 0
    layers = ["web_server", "nginx", "grpc_auth", "envoy", "haproxy"]
    layer_latencies = {}
    for layer in layers:
        # Simulate latency for the current layer
        latency = min(simulate_latency_log_normal(avg_latencies[layer], timeouts[layer]), timeouts[layer])
        layer_latencies[layer] = latency
        
        # Multiply the latency by how far behind in the queue for the layer the request is
        latency *= layer_backlogs[layer] + 1

        # Add the current layer's latency to the cumulative latency
        cumulative_latency += latency

        # If at any point the cumulative latency exceeds the timeout of the current layer
        # and all layers beneath it (i.e., including this and future layers), the request times out.
        if cumulative_latency >= timeouts[layer] and layer != "grpc_auth":
            # GRPC returns back to envoy I think?? so doesn't include layers below
            return cumulative_latency, True, layer  # Request timed out
        if layer == "grpc_auth" and latency >= timeouts[layer]:
            # GRPC returns back to envoy I think?? so doesn't include layers below
            return cumulative_latency, True, layer  # Request timed out

    return cumulative_latency, False, None  # Request succeeded


# Function to simulate multiple requests
def simulate_requests(n_requests, layer_timeouts, avg_latencies, layer_backlogs):
    timeouts = {}
    latencies = []
    timeout_latencies = []

    for _ in range(n_requests):
        total_latency, timed_out, layer = simulate_request(
            layer_timeouts, avg_latencies, layer_backlogs
        )
        if timed_out:
            if layer in timeouts:
                timeouts[layer] += 1
            else:
                timeouts[layer] = 1
            timeout_latencies.append(total_latency)
        else:
            latencies.append(total_latency)

    return latencies, timeouts, timeout_latencies


# Main simulation
if __name__ == "__main__":
    try:
        web_server_avg_latency = float(
            input(
                "Enter the average latency for the web server (in seconds) (default 1): "
            ).strip()
            or "1"
        )
        web_server_backlog = int(
            input(
                "How many requests behind is the web server (backlog queue) (default 10): "
            ).strip()
            or "10"
        )
        #web_server_lose_requests_percent = int(
        #    input(
        #        "What percentage of requests fall of queue at web server? (default 0.01)"
        #    ).strip()
        #    or "0.01"
        #)
        grpc_auth_avg_latency = float(
            input(
                "Enter the average latency for the grpc auth server (in seconds) (default 0.05): "
            ).strip()
            or "0.05"
        )
        grpc_backlog = int(
            input(
                "How many requests behind is the grpc server (backlog queue) (default 10): "
            ).strip()
            or "10"
        )
        haproxy_timeout = float(
            input(
                "Enter the timeout for loadbalancer (in seconds) (default 30): "
            ).strip()
            or "30"
        )
        envoy_timeout = float(
            input("Enter the timeout for envoy (in seconds) (default 30): ").strip()
            or "30"
        )
        grpc_auth_timeout = float(
            input("Enter the timeout for grpc_auth (in seconds) (default 10): ").strip()
            or "10"
        )
        nginx_timeout = float(
            input("Enter the timeout for nginx (in seconds) (default 60): ").strip()
            or "60"
        )
        webserver_timeout = float(
            input(
                "Enter the timeout for the web server (in seconds) (default 120): "
            ).strip()
            or "120"
        )
        n_requests = 10000
        # Layer parameters (Timeouts and average latencies)
        layer_timeouts = {
            "haproxy": haproxy_timeout,
            "envoy": envoy_timeout,
            "grpc_auth": grpc_auth_timeout,
            "nginx": nginx_timeout,
            "web_server": webserver_timeout,
        }
        layer_backlogs = {
            "web_server": web_server_backlog,
            "nginx": 0,
            "grpc_auth": grpc_backlog,
            "envoy": 0,
            "haproxy": 0,
        }

        avg_latencies = {
            "haproxy": 0.01,  # 10ms
            "envoy": 0.01,  # 10ms
            "grpc_auth": grpc_auth_avg_latency,
            "nginx": 0.01,  # 10ms
            "web_server": web_server_avg_latency,
        }
        latencies, timeouts, timeout_latencies = simulate_requests(
            n_requests, layer_timeouts, avg_latencies, layer_backlogs
        )

        # Print statistics
        print(f"Total Requests: {n_requests}")
        print(f"Timed Out Requests: {sum(timeouts.values())}")
        print(f"Successful Requests: {n_requests - sum(timeouts.values())}")

        # Print the number of timeouts at each layer
        print("Timeouts by layer:")
        for layer, count in timeouts.items():
            print(f"{layer}: {count}")

        # Plot histogram of latencies
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.hist(
            latencies,
            bins=50,
            edgecolor="black",
            alpha=0.7,
            label="Successful Requests",
        )
        ax.hist(
            timeout_latencies,
            bins=50,
            edgecolor="red",
            alpha=0.7,
            label="Timed Out Requests",
        )

        # Add info box with additional statistics
        info_box_text = (
            f"Layer Timeouts:\n"
            + "\n".join(
                [f"{layer}: {count}s, hit {timeouts.get(layer, 0)} times" for layer, count in layer_timeouts.items()]
            )
            + "\n\n"
            + f"Layer Avg Latency:\n"
            + "\n".join(
                [f"{layer}: {latency:.3f}s" for layer, latency in avg_latencies.items()]
            )
            + "\n"
            + f"Webserver Backlog: {web_server_backlog}\n"
            + f"GRPC Auth Server Backlog: {grpc_backlog}\n"
        )

        # Add a text box to the plot
        ax.text(
            0.7,
            0.35,
            info_box_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="bottom",
            horizontalalignment="right",
            bbox=dict(facecolor="white", edgecolor="black", boxstyle="round,pad=1"),
        )

        # Inset pie chart for success vs timeout count
        success_count = n_requests - sum(timeouts.values())
        timeout_count = sum(timeouts.values())

        # Pie chart data and labels
        sizes = [success_count, timeout_count]
        labels = [f"Successful ({success_count})", f"Timed Out ({timeout_count})"]
        colors = ["#66b3ff", "#ff6666"]
        explode = (0.1, 0)  # "explode" the first slice (successful)

        # Add inset pie chart
        ax_inset = fig.add_axes([0.6, 0.15, 0.2, 0.2])  # Inset axis location
        ax_inset.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            explode=explode,
        )
        ax_inset.axis("equal")  # Equal aspect ratio ensures that pie chart is circular.

        ax.set_title("Histogram of Latencies")
        ax.set_xlabel("Latency (seconds)")
        ax.set_ylabel("Frequency")

        # Save the figure with the input in the filename
        filename = f"simulation_results_web_server_latency.png"
        plt.savefig(filename)
        print(f"Figure saved as {filename}")

        # Show the plot with the inset pie chart
        plt.show()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.exit(0)
