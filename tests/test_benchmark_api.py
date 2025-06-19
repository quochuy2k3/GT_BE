"""
Test script for Benchmark API
Demonstrates how to use the benchmark endpoint
"""

import requests
import json
import time
import asyncio
import httpx
from pathlib import Path


class BenchmarkAPITester:
    def __init__(self, base_url="http://localhost:8000", jwt_token=None):
        self.base_url = base_url
        self.jwt_token = jwt_token
        self.headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}
    
    def test_benchmark_sync(self, image_path, concurrent_requests=10):
        """
        Test benchmark API using synchronous requests
        """
        print(f"🚀 Testing Benchmark API with {concurrent_requests} concurrent requests")
        print(f"📁 Image: {image_path}")
        
        url = f"{self.base_url}/predict/benchmark"
        
        try:
            with open(image_path, 'rb') as f:
                files = {
                    "file": (Path(image_path).name, f, "image/jpeg")
                }
                data = {
                    "concurrent_requests": concurrent_requests
                }
                
                start_time = time.time()
                response = requests.post(url, headers=self.headers, files=files, data=data)
                end_time = time.time()
                
                print(f"⏱️  Total request time: {(end_time - start_time):.2f} seconds")
                print(f"📊 Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    self.print_benchmark_results(result)
                else:
                    print(f"❌ Error: {response.text}")
                    
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
    
    async def test_benchmark_async(self, image_path, concurrent_requests=10):
        """
        Test benchmark API using asynchronous requests
        """
        print(f"🚀 Testing Benchmark API (Async) with {concurrent_requests} concurrent requests")
        print(f"📁 Image: {image_path}")
        
        url = f"{self.base_url}/predict/benchmark"
        
        try:
            async with httpx.AsyncClient() as client:
                with open(image_path, 'rb') as f:
                    files = {
                        "file": (Path(image_path).name, f, "image/jpeg")
                    }
                    data = {
                        "concurrent_requests": concurrent_requests
                    }
                    
                    start_time = time.time()
                    response = await client.post(url, headers=self.headers, files=files, data=data)
                    end_time = time.time()
                    
                    print(f"⏱️  Total request time: {(end_time - start_time):.2f} seconds")
                    print(f"📊 Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        self.print_benchmark_results(result)
                    else:
                        print(f"❌ Error: {response.text}")
                        
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
    
    def print_benchmark_results(self, result):
        """
        Pretty print benchmark results
        """
        print("\n" + "="*60)
        print("📈 BENCHMARK RESULTS")
        print("="*60)
        
        # Basic info
        info = result.get("benchmark_info", {})
        print(f"⏰ Timestamp: {info.get('timestamp')}")
        print(f"🔢 Concurrent Requests: {info.get('concurrent_requests')}")
        print(f"⏱️  Total Time: {info.get('total_benchmark_time_ms')} ms")
        print(f"📄 File: {info.get('file_name')} ({info.get('file_size_bytes')} bytes)")
        
        # Performance metrics
        metrics = result.get("performance_metrics", {})
        print(f"\n✅ Success Rate: {metrics.get('success_rate_percent')}%")
        print(f"📊 Successful: {metrics.get('success_count')}")
        print(f"❌ Failed: {metrics.get('failure_count')}")
        print(f"🚀 Throughput: {metrics.get('throughput_rps')} RPS")
        
        # Response time stats
        time_stats = metrics.get("response_time_stats_ms", {})
        print(f"\n⏱️  Response Time Statistics (ms):")
        print(f"   Average: {time_stats.get('average')}")
        print(f"   Median:  {time_stats.get('median')}")
        print(f"   Min:     {time_stats.get('minimum')}")
        print(f"   Max:     {time_stats.get('maximum')}")
        print(f"   P95:     {time_stats.get('p95')}")
        print(f"   P99:     {time_stats.get('p99')}")
        
        # Failed requests
        failed = result.get("detailed_results", {}).get("failed_requests", [])
        if failed:
            print(f"\n❌ Failed Requests ({len(failed)}):")
            for req in failed[:5]:  # Show first 5 failures
                print(f"   Request {req.get('request_id')}: {req.get('error')}")
        
        print("="*60)
    
    def run_progressive_benchmark(self, image_path, max_concurrent=20, step=5):
        """
        Run benchmark with increasing concurrent requests
        """
        print("🔄 Running Progressive Benchmark")
        print("="*50)
        
        for concurrent in range(step, max_concurrent + 1, step):
            print(f"\n📊 Testing with {concurrent} concurrent requests...")
            self.test_benchmark_sync(image_path, concurrent)
            time.sleep(2)  # Wait between tests


def main():
    """
    Main function to run benchmark tests
    """
    # Configuration
    BASE_URL = "http://localhost:8000"
    JWT_TOKEN = "your_jwt_token_here"  # Replace with actual token
    IMAGE_PATH = "../temp/00aa5dcc-fa36-411f-8e26-6385cdf7a284.jpg"  # Use any test image
    
    # Initialize tester
    tester = BenchmarkAPITester(BASE_URL, JWT_TOKEN)
    
    # Check if image exists
    if not Path(IMAGE_PATH).exists():
        print(f"❌ Image not found: {IMAGE_PATH}")
        print("Please update IMAGE_PATH with a valid image file")
        return
    
    # Run tests
    print("🧪 Starting Benchmark API Tests")
    print("="*50)
    
    # Test 1: Basic benchmark
    print("\n1️⃣  Basic Benchmark Test")
    tester.test_benchmark_sync(IMAGE_PATH, concurrent_requests=5)
    
    # Test 2: Async benchmark
    print("\n2️⃣  Async Benchmark Test")
    asyncio.run(tester.test_benchmark_async(IMAGE_PATH, concurrent_requests=5))
    
    # Test 3: Progressive benchmark (uncomment to run)
    # print("\n3️⃣  Progressive Benchmark Test")
    # tester.run_progressive_benchmark(IMAGE_PATH, max_concurrent=15, step=3)


if __name__ == "__main__":
    main() 