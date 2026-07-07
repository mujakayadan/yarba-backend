# Frontend Polling Guidelines

## Issue
The backend detected excessive polling (300ms intervals for 15+ minutes) to the portfolio website endpoints. This causes unnecessary server load and database queries.

## Problem Endpoints
- `GET /api/v1/portfolio-websites/` - Main portfolio website endpoint
- `GET /api/v1/portfolio-websites/deployment-status` - Deployment status endpoint

## Solutions Implemented

### 1. Caching Headers
The API now returns appropriate `Cache-Control` headers based on deployment status:
- **Building**: 2-5 seconds cache
- **Success/Failed**: 30-60 seconds cache
- **Default**: 5-10 seconds cache

### 2. Recommended Poll Intervals
The API includes a custom header `X-Recommended-Poll-Interval` that indicates the optimal polling interval in seconds.

### 3. Rate Limiting
- Main endpoint: 60 requests/minute
- Deployment status: 60 requests/minute
- Other portfolio endpoints: 30 requests/minute

## Frontend Best Practices

### ✅ DO
1. **Respect Cache Headers**: Use the `Cache-Control` header to avoid unnecessary requests
2. **Use Recommended Intervals**: Check the `X-Recommended-Poll-Interval` header
3. **Exponential Backoff**: For failed requests, use exponential backoff
4. **Stop Polling**: Stop polling when deployment is complete (success/failed status)
5. **Use Proper Intervals**:
   - Building: Poll every 5 seconds max
   - Completed states: Poll every 30-60 seconds or stop entirely
   - Never poll faster than 2 seconds

### ❌ DON'T
1. **Don't poll at 300ms intervals** - This is excessive and causes server strain
2. **Don't poll indefinitely** - Set a maximum timeout (e.g., 10 minutes)
3. **Don't ignore rate limit responses** - Handle 429 status codes properly
4. **Don't poll completed deployments** - No need to check success/failed states repeatedly

### Example Implementation

```javascript
class DeploymentPoller {
  constructor() {
    this.polling = false;
    this.timeoutId = null;
    this.maxRetries = 50; // 10 minutes at 5s intervals
    this.retryCount = 0;
  }

  async pollDeploymentStatus() {
    if (this.retryCount >= this.maxRetries) {
      console.warn('Deployment polling timeout after 10 minutes');
      this.stopPolling();
      return;
    }

    try {
      const response = await fetch('/api/v1/portfolio-websites/deployment-status');

      if (response.status === 429) {
        // Rate limited - wait longer
        const interval = 10000; // 10 seconds
        this.scheduleNextPoll(interval);
        return;
      }

      const data = await response.json();
      const recommendedInterval = response.headers.get('X-Recommended-Poll-Interval');

      // Check if deployment is complete
      if (['success', 'failed'].includes(data.status)) {
        this.stopPolling();
        this.handleDeploymentComplete(data);
        return;
      }

      // Schedule next poll using recommended interval
      const interval = (parseInt(recommendedInterval) || 5) * 1000;
      this.scheduleNextPoll(interval);

    } catch (error) {
      console.error('Polling error:', error);
      // Exponential backoff for errors
      const interval = Math.min(30000, 5000 * Math.pow(2, this.retryCount));
      this.scheduleNextPoll(interval);
    }

    this.retryCount++;
  }

  scheduleNextPoll(interval) {
    this.timeoutId = setTimeout(() => {
      this.pollDeploymentStatus();
    }, interval);
  }

  startPolling() {
    if (!this.polling) {
      this.polling = true;
      this.retryCount = 0;
      this.pollDeploymentStatus();
    }
  }

  stopPolling() {
    this.polling = false;
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
  }

  handleDeploymentComplete(data) {
    console.log('Deployment completed:', data.status);
    // Update UI accordingly
  }
}
```

## Monitoring
The backend logs will show rate limit violations and cache hits. Monitor these to ensure proper frontend behavior.
