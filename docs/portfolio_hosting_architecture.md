# Portfolio Website Hosting Architecture (`subdomain.yarba.app`)

This document outlines the technical architecture for hosting multi-tenant portfolio websites under subdomains of `yarba.app` (e.g., `mujakayadan.yarba.app`, `user1.yarba.app`). The solution leverages Vercel for DNS management and AWS services (S3, CloudFront, ACM, CloudFront Functions) for content storage, delivery, and security.

## Core Components

*   **Vercel**: DNS hosting for `yarba.app`.
*   **AWS S3 (Simple Storage Service)**: Stores the static website files (HTML, CSS, JS, images) for each portfolio.
*   **AWS CloudFront**: Global Content Delivery Network (CDN) to serve website content quickly and securely.
*   **AWS Certificate Manager (ACM)**: Provides SSL/TLS certificates for `*.yarba.app`.
*   **CloudFront Functions**: Edge compute to rewrite request URIs dynamically based on the subdomain.
*   **Yarba Backend Application**: Handles website generation, deployment to S3, and CloudFront cache invalidation.

## Request Flow for `subdomain.yarba.app`

1.  **DNS Resolution**:
    *   User enters `https://subdomain.yarba.app` in their browser.
    *   Browser queries DNS for `subdomain.yarba.app`.
    *   Vercel DNS returns a CNAME record pointing `*.yarba.app` to the CloudFront distribution's domain name.
2.  **CloudFront Request**:
    *   Browser connects to the CloudFront edge location.
    *   CloudFront uses the `*.yarba.app` Alternate Domain Name and the associated ACM SSL certificate to handle the HTTPS request.
3.  **CloudFront Function (Viewer Request)**:
    *   The `rewrite-uri-for-subdomain-portfolios` CloudFront Function executes.
    *   It inspects the `Host` header (e.g., `subdomain.yarba.app`) to extract the `subdomain`.
    *   It rewrites the request URI. For example:
        *   Request for `/` becomes `/portfolios/subdomain/index.html`.
        *   Request for `/style.css` becomes `/portfolios/subdomain/style.css`.
4.  **CloudFront Origin Request**:
    *   CloudFront, using the rewritten URI, requests the object from the S3 origin.
    *   Origin Access Control (OAC) is used to securely allow CloudFront to access the S3 bucket.
5.  **S3 Response**:
    *   S3 serves the requested object (e.g., `/portfolios/subdomain/index.html`) if the S3 bucket policy grants permission to the CloudFront OAC.
6.  **CloudFront Response & Caching**:
    *   CloudFront receives the object from S3.
    *   It caches the object at the edge location according to the cache policy.
    *   It serves the object to the user's browser.
7.  **Subsequent Requests**: If the content is cached, CloudFront serves it directly from the edge, improving performance.

## Configuration Details

### 1. Vercel DNS Configuration (for `yarba.app`)

*   **Wildcard CNAME Record**:
    *   **Type**: `CNAME`
    *   **Name/Host**: `*`
    *   **Value/Points to**: Your CloudFront distribution's domain name (e.g., `d111111abcdef8.cloudfront.net`).
*   **CAA Records**: To allow AWS Certificate Manager to issue certificates.
    *   `0 issue "amazon.com"`
    *   `0 issue "amazonaws.com"`
    *   `0 issue "amazontrust.com"`
    *   `0 issue "awstrust.com"`

### 2. AWS Certificate Manager (ACM)

*   A **wildcard SSL certificate** for `*.yarba.app`.
*   **Region**: Must be `us-east-1` (N. Virginia) for use with CloudFront.
*   **Status**: "Issued" and associated with the CloudFront distribution.
    *   Record the certificate ID securely in your infrastructure configuration.

### 3. CloudFront Distribution

*   **General Settings**:
    *   **Price Class**: "Use all edge locations (best performance)".
    *   **Alternate Domain Names (CNAMEs)**: `*.yarba.app`.
    *   **Custom SSL Certificate**: The `*.yarba.app` ACM certificate.
    *   **Supported HTTP Versions**: HTTP/2, HTTP/1.1, HTTP/1.0.
    *   **Default Root Object**: `index.html`.
*   **Origin Settings (`s3-portfolios-origin`)**:
    *   **Origin Domain**: S3 bucket endpoint (e.g., `your-portfolio-bucket.s3.us-east-1.amazonaws.com`).
    *   **Origin Path**: **Must be empty.**
    *   **Origin Access**:
        *   Selected: `Origin access control settings (recommended)`.
        *   Origin Access Control (OAC) entity selected: `portfolio-bucket-oac`.
*   **Behavior Settings (Default `*` Path Pattern)**:
    *   **Origin and origin groups**: `s3-portfolios-origin`.
    *   **Viewer Protocol Policy**: "Redirect HTTP to HTTPS" or "HTTPS only".
    *   **Allowed HTTP Methods**: "GET, HEAD" (or "GET, HEAD, OPTIONS" if needed).
    *   **Compress objects automatically**: "Yes".
    *   **Cache Policy**: An appropriate policy like `CachingOptimized` or a custom one.
    *   **Origin Request Policy**: A suitable policy, often minimal for S3 static content.
    *   **Function Associations (Viewer Request)**:
        *   **Function type**: `CloudFront Functions`.
        *   **Function ARN / Name**: `rewrite-uri-for-subdomain-portfolios`.

### 4. CloudFront Function (`rewrite-uri-for-subdomain-portfolios`)

*   **Purpose**: To dynamically rewrite the request URI based on the subdomain in the `Host` header, allowing a single S3 bucket structure to serve multiple portfolio sites.
*   **Event Trigger**: Viewer Request.
*   **Code Snippet**:
    ```javascript
    function handler(event) {
        var request = event.request;
        var host = request.headers.host.value; // e.g., "mujakayadan.yarba.app"
        var subdomain = host.split('.')[0];

        // Prepend /portfolios/subdomain to the original URI
        var newUri = '/portfolios/' + subdomain + request.uri;

        // Ensure that requests for the root of the subdomain (e.g., /)
        // are directed to index.html within the subdomain's folder.
        // Also handle cases where the original URI might be empty for root requests.
        if (newUri.endsWith('/') || request.uri === "") {
             if (request.uri.lastIndexOf('.') < request.uri.lastIndexOf('/')) { // Check if it's likely a directory
                 newUri = newUri.replace(/\/$/, "") + '/index.html';
             } else if (request.uri === "") { // Explicitly handle empty original URI for root
                 newUri = '/portfolios/' + subdomain + '/index.html';
             }
        }

        request.uri = newUri.replace(/\/\//g, '/'); // Prevent double slashes

        return request;
    }
    ```

### 5. S3 Bucket

*   **Content Structure**: Static website files are organized as follows:
    `s3://your-portfolio-bucket/portfolios/<subdomain_name>/index.html`
    `s3://your-portfolio-bucket/portfolios/<subdomain_name>/style.css`
    `s3://your-portfolio-bucket/portfolios/<subdomain_name>/images/image.jpg`
    Other folders like `profile-pictures/` and `resumes/` exist for different application purposes and are not directly served by this CloudFront distribution setup.
*   **Bucket Policy**:
    The second statement is optional and only needed when CloudFront access
    logging is enabled.

    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontAccessToPortfoliosViaOACCondition",
                "Effect": "Allow",
                "Principal": {
                    "Service": "cloudfront.amazonaws.com"
                },
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::your-portfolio-bucket/portfolios/*",
                "Condition": {
                    "StringEquals": {
                        "AWS:SourceArn": "arn:aws:cloudfront::YOUR_AWS_ACCOUNT_ID:distribution/YOUR_CLOUDFRONT_DISTRIBUTION_ID"
                    }
                }
            },
            {
                "Sid": "AWSLogDeliveryWrite1",
                "Effect": "Allow",
                "Principal": {
                    "Service": "delivery.logs.amazonaws.com"
                },
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::your-portfolio-bucket/AWSLogs/YOUR_AWS_ACCOUNT_ID/CloudFront/*",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": "YOUR_AWS_ACCOUNT_ID",
                        "s3:x-amz-acl": "bucket-owner-full-control"
                    },
                    "ArnLike": {
                        "aws:SourceArn": "arn:aws:logs:us-east-1:YOUR_AWS_ACCOUNT_ID:delivery-source:CreatedByCloudFront-YOUR_CLOUDFRONT_DISTRIBUTION_ID"
                    }
                }
            }
        ]
    }
    ```
    Replace `YOUR_AWS_ACCOUNT_ID` and `YOUR_CLOUDFRONT_DISTRIBUTION_ID` with values from your own AWS account.

### 6. Application Logic (YARBA Backend)

*   The `PortfolioWebsiteService` is responsible for creating the website data.
*   The `WebsiteGeneratorService` generates the static HTML, CSS, and JS files.
*   The `AWSDeploymentService` uploads these generated files to the correct S3 path: `s3://your-portfolio-bucket/portfolios/<subdomain>/`.
*   `AWSDeploymentService` also triggers a CloudFront cache invalidation for `/portfolios/<subdomain>/*` after successful deployment to ensure users see the latest version.

## Key Considerations & Troubleshooting

*   **DNS Propagation**: Changes to DNS records (especially CNAMEs) can take time to propagate globally.
*   **CloudFront Deployment Time**: Changes to CloudFront distributions (settings, function associations) can take 5-20 minutes or more to deploy across all edge locations.
*   **S3 Bucket Policy Precision**: Ensure the `Resource` and `Condition` clauses in the S3 bucket policy are accurate to grant necessary permissions without being overly permissive. The `AWS:SourceArn` condition is crucial for security when using `Principal: { "Service": "cloudfront.amazonaws.com" }` with OAC.
*   **CloudFront Function Testing**: Thoroughly test the CloudFront Function with various URIs and host headers to ensure it rewrites paths correctly.
*   **Cache Invalidation**: Remember to invalidate the CloudFront cache after deploying new content to S3 to avoid serving stale content.
*   **OAC vs. OAI**: This setup uses Origin Access Control (OAC). The S3 bucket policy must correctly reflect the OAC setup. The `Principal` in the S3 policy for OAC is typically the general `cloudfront.amazonaws.com` service, secured by the `AWS:SourceArn` condition that ties it to the specific CloudFront distribution configured with the OAC entity.

This architecture provides a robust, scalable, and secure platform for hosting dynamic user portfolio websites.
