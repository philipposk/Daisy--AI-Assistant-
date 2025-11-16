#!/usr/bin/env node

/**
 * Benchmark Tests for MCP Desktop Automation Server
 * Measures performance of critical functions
 */

function benchmark(name, fn, iterations = 1000) {
  const start = process.hrtime.bigint();
  const startMemory = process.memoryUsage().heapUsed;
  
  for (let i = 0; i < iterations; i++) {
    fn();
  }
  
  const end = process.hrtime.bigint();
  const endMemory = process.memoryUsage().heapUsed;
  
  const timeMs = Number(end - start) / 1_000_000; // Convert to milliseconds
  const memoryMB = (endMemory - startMemory) / 1024 / 1024;
  
  console.log(`\n⏱️  ${name}`);
  console.log(`   Time: ${(timeMs / iterations).toFixed(4)}ms per operation`);
  console.log(`   Total: ${timeMs.toFixed(2)}ms for ${iterations} iterations`);
  console.log(`   Memory: ${memoryMB.toFixed(2)}MB`);
  
  return {
    timePerOp: timeMs / iterations,
    totalTime: timeMs,
    memoryDelta: memoryMB,
  };
}

console.log('🚀 Running Benchmarks...\n');

// Benchmark 1: Error Detection
benchmark('Error Detection (CocoaPods)', () => {
  const logText = "Error: pod not found. Please run pod install";
  const pattern = /pod.*not found|CocoaPods/i;
  pattern.test(logText);
}, 10000);

// Benchmark 2: Pattern Matching
benchmark('Pattern Matching (Multiple Patterns)', () => {
  const logText = "Error: npm package not found";
  const patterns = [
    /pod.*not found|CocoaPods/i,
    /npm.*not found|package.*not found/i,
    /python.*not found|ModuleNotFoundError/i,
  ];
  patterns.forEach(p => p.test(logText));
}, 10000);

// Benchmark 3: JSON Parsing
benchmark('JSON Parsing (Error Result)', () => {
  const result = {
    success: false,
    errors: [{
      type: "missing_dependency",
      message: "CocoaPods dependency missing",
      fix: "pod install",
    }],
    suggestions: ["pod install"],
  };
  JSON.stringify(result);
}, 10000);

// Benchmark 4: String Operations
benchmark('String Operations (Log Analysis)', () => {
  const logText = "Build failed with error: pod not found";
  logText.toLowerCase();
  logText.includes("error");
  logText.match(/error|failed/i);
}, 100000);

console.log('\n✅ Benchmarks complete!\n');

