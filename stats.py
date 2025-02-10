import pyshark
from google.cloud import bigquery
import json
import os
import time
import threading

# BigQuery client setup
client = bigquery.Client()
dataset_id = 'ferrous-ranger-448206-v2.network_traffic'  # Replace with your dataset
table_id = f'{dataset_id}.network_traffic_data'

# File path for saving the captured data temporarily
output_file = '/tmp/network_traffic.json'

# Function to load data from file to BigQuery
def load_data_to_bigquery(file_path):
    print(f"Uploading data from {file_path} to BigQuery...")
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
    )

    # Read the JSON file and load it to BigQuery
    with open(file_path, "rb") as file:
        load_job = client.load_table_from_file(file, table_id, job_config=job_config)

    load_job.result()  # Wait for the job to complete
    print(f"Loaded {load_job.output_rows} rows into {table_id}.")

# Function to periodically upload data
def periodic_upload():
    while True:
        time.sleep(60)  # Upload every 60 seconds (adjust as needed)
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            load_data_to_bigquery(output_file)
            open(output_file, 'w').close()  # Clear the file after uploading

# Function to capture traffic and process each packet
def capture_traffic():
    capture = pyshark.LiveCapture(interface='en0', display_filter='tcp or udp or http or tls.handshake')  # Capture TCP, UDP, HTTP, and TLS handshakes
    captured_data = []
    total_packets = 0

    print("Capturing packets... Press Ctrl+C to stop.")
    for packet in capture.sniff_continuously():
        try:
            if 'IP' in packet:
                row = {
                    "timestamp": packet.sniff_time.isoformat(),
                    "src_ip": packet.ip.src,
                    "dst_ip": packet.ip.dst,
                    "protocol": packet.transport_layer if 'IP' in packet else "N/A",
                    "host": "N/A",
                    "request_uri": "N/A"
                }

                # Capture HTTP details
                if 'HTTP' in packet:
                    row["protocol"] = 'HTTP'
                    row["host"] = getattr(packet.http, 'host', "N/A")
                    row["request_uri"] = getattr(packet.http, 'request_uri', "N/A")

                # Capture HTTPS details from TLS handshake
                elif 'TLS' in packet:
                    row["protocol"] = 'HTTPS'
                    row["host"] = getattr(packet.tls, 'handshake_extensions_server_name', "N/A")


                captured_data.append(row)
                total_packets += 1

                # Write the captured data to file periodically (e.g., every 100 rows)
                if len(captured_data) >= 100:  # Adjust batch size as needed
                    with open(output_file, 'a') as f:
                        for data in captured_data:
                            json.dump(data, f)
                            f.write('\n')  # Write each entry on a new line
                    print(f"Captured {total_packets} packets and written to {output_file}")
                    captured_data.clear()  # Clear the batch to avoid growing memory usage

        except AttributeError:
            continue

    return total_packets

# Main function
def main():
    try:
        # Start the periodic upload in a separate thread
        upload_thread = threading.Thread(target=periodic_upload, daemon=True)
        upload_thread.start()

        # Capture and write data to the file
        total_packets = capture_traffic()
        print(f"Captured a total of {total_packets} packets.")

    except KeyboardInterrupt:
        print("\nCapture stopped by user. Uploading captured data to BigQuery...")

        # Ensure data is uploaded even if the capture ends prematurely
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            load_data_to_bigquery(output_file)
            # Clear the file after uploading to avoid re-uploading the same data
            open(output_file, 'w').close()
        else:
            print("No data captured or file is empty.")

    except EOFError:
        print("Capture stream ended unexpectedly. Uploading captured data to BigQuery...")

        # Ensure data is uploaded when stream ends unexpectedly
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            load_data_to_bigquery(output_file)
            # Clear the file after uploading to avoid re-uploading the same data
            open(output_file, 'w').close()

if __name__ == '__main__':
    main()

