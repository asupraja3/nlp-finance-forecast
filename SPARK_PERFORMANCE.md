# Spark Performance Optimization Guide

## Overview
This document describes the performance optimizations implemented in the Spark jobs for the NLP Finance Forecast pipeline.

## Key Optimizations Implemented

### 1. Spark Configuration Enhancements

#### Feature Engineering Job (`src/feature_engineering.py`)
- **Dynamic Resource Allocation**: `master("local[*]")` - Uses all available CPU cores
- **Adaptive Query Execution (AQE)**: Enabled for runtime optimization
  - `spark.sql.adaptive.enabled = true`
  - `spark.sql.adaptive.coalescePartitions.enabled = true`
  - `spark.sql.adaptive.skewJoin.enabled = true`
- **Memory Management**:
  - Driver memory: 4GB
  - Executor memory: 4GB
  - Memory fraction: 0.8 (80% for execution/storage)
  - Storage fraction: 0.3 (30% of memory for caching)
- **Parallelism**:
  - Shuffle partitions: 200 (optimal for medium to large datasets)
  - Default parallelism: 200
- **Broadcast Join**: Threshold set to 10MB for automatic optimization

#### Training Job (`src/train.py`)
- **Dynamic Resource Allocation**: Uses all available cores
- **Adaptive Query Execution**: Enabled for query optimization
- **Kryo Serializer**: Faster serialization for model training
- **Memory**: 4GB driver and executor memory
- **Partitions**: 200 shuffle partitions for distributed training

#### Prediction Job (`src/predict.py`)
- **Lightweight Configuration**: Optimized for inference workload
- **Adaptive Query Execution**: Enabled
- **Reduced Partitions**: 10 shuffle partitions (sufficient for small prediction datasets)
- **Memory**: 2GB driver and executor memory

### 2. Data Caching Strategy

#### When to Cache
- **Stock Data**: Cached after loading and cleaning (reused in feature engineering)
- **News Data**: Cached before sentiment analysis (expensive operation)
- **Training Data**: Cached when loaded for model training

#### Benefits
- Avoids recomputation of expensive transformations
- Reduces I/O operations
- Improves iterative algorithm performance

#### Memory Management
- All cached DataFrames are explicitly unpersisted after use
- Prevents memory leaks in long-running jobs

### 3. Broadcast Join Optimization

The feature engineering job uses intelligent join strategy:

```python
if sentiment_count < 10000:
    # Use broadcast join for small datasets
    final_df = features_df.join(broadcast(sentiment_df), on="Date", how="left")
else:
    # Use standard join for large datasets
    final_df = features_df.join(sentiment_df, on="Date", how="left")
```

**Benefits**:
- Eliminates shuffle for small dimension tables
- Reduces network I/O
- Faster execution for typical date-based joins

### 4. Partition Management

#### Output Partitioning
Smart coalescing based on data size:
- Small datasets (< 100K rows): 1 partition
- Medium datasets (100K - 1M rows): 10 partitions
- Large datasets (> 1M rows): Default partitioning

**Benefits**:
- Reduces small file problem
- Optimizes downstream read performance
- Balances parallelism with file management

### 5. Data Limits Removed

**Previous Issue**: Code had hardcoded `.limit(50)` for testing
**Solution**: Removed all artificial limits to enable full-scale processing

### 6. Arrow Optimization

`spark.sql.execution.arrow.pyspark.enabled = true`

**Benefits**:
- Faster conversion between Spark and Pandas DataFrames
- Vectorized data transfer
- Reduced serialization overhead

## Performance Monitoring

### Built-in Logging
All jobs now include:
- Row count logging at key stages
- Data volume tracking
- Processing time indicators

### Spark UI
Access at `http://localhost:4040` when jobs are running to monitor:
- Stage execution times
- Shuffle read/write volumes
- Task distribution
- Memory usage
- DAG visualization

## Scaling Guidelines

### For Small Datasets (< 100K rows)
Current configuration is optimal. Consider:
- Reducing shuffle partitions to 10-50
- Lowering memory allocation to 2GB

### For Medium Datasets (100K - 10M rows)
Current configuration is optimal.

### For Large Datasets (> 10M rows)
Consider:
- Increasing shuffle partitions to 400-800
- Increasing driver/executor memory to 8GB or more
- Using standalone Spark cluster instead of local mode
- Implementing checkpointing for fault tolerance
- Using Parquet partition columns for date-based queries

### For Very Large Datasets (> 100M rows)
Consider:
- Migrating to distributed cluster (EMR, Dataproc, Databricks)
- Using dynamic allocation with external shuffle service
- Implementing incremental processing
- Using Delta Lake for ACID transactions
- Partitioning output data by date/year/month

## Best Practices Applied

1. **Data Caching**: Applied to frequently accessed DataFrames
2. **Broadcast Joins**: Used for small dimension tables
3. **Partition Tuning**: Optimized for data volume
4. **Memory Management**: Explicit unpersist operations
5. **Adaptive Query Execution**: Enabled for runtime optimization
6. **Kryo Serialization**: Used for faster object serialization
7. **Arrow Integration**: Enabled for Pandas interoperability
8. **Resource Allocation**: Dynamic allocation based on available resources
9. **File Consolidation**: Coalescing for optimal file sizes
10. **Monitoring**: Enhanced logging for performance visibility

## Troubleshooting

### Out of Memory Errors
- Increase driver/executor memory
- Reduce batch size for UDFs
- Add checkpointing
- Reduce shuffle partitions if too many small tasks

### Slow Shuffle Operations
- Increase shuffle partitions
- Check for data skew (use AQE skew join handling)
- Consider salting keys for skewed joins

### Slow UDF Performance
- Current sentiment UDF processes rows sequentially
- For further optimization, consider:
  - Converting to Pandas UDF with batch processing
  - Pre-computing sentiment scores offline
  - Using a sentiment analysis microservice

## Future Enhancements

1. **Pandas UDF**: Convert sentiment analysis to vectorized Pandas UDF
2. **Checkpoint Support**: Add checkpointing for fault tolerance
3. **Dynamic Scaling**: Implement auto-scaling based on data volume
4. **Partition Pruning**: Add date-based partitioning to output Parquet files
5. **Monitoring Integration**: Add Spark metrics to monitoring system
6. **Cluster Mode**: Support for standalone/YARN/K8s deployment
