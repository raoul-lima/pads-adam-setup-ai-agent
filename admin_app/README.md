# Adam Agent Admin Dashboard

A Next.js admin dashboard for viewing user feedback from the Adam Agent system.

## Features

- **Static Authentication**: Login with predefined credentials
- **Feedback Dashboard**: View and filter user feedback data
- **Real-time Data**: Fetches feedback from cloud storage JSON endpoint
- **Responsive Design**: Built with Tailwind CSS
- **TypeScript**: Fully typed application

## Setup

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Environment Configuration**:
   Create a `.env.local` file with:
   ```env
   # Basic configuration
   ADMIN_USERNAME=admin_adam_agent
   ADMIN_PASSWORD=admin@adam_Agent123


   # Option 2: Google Cloud Storage Authentication (recommended for private files)
   GCS_SERVICE_ACCOUNT_KEY_BASE64=your_base64_encoded_service_account_key
   GCS_BUCKET_NAME=your-bucket-name
   GCS_FILE_NAME=feedback.json
   ```

   ### Setting up Google Cloud Storage Authentication

   For private GCS files, you'll need a service account key:

   1. **Create a Service Account**:
      - Go to Google Cloud Console → IAM & Admin → Service Accounts
      - Create a new service account with Storage Object Viewer permissions

   2. **Download the Key**:
      - Generate and download the JSON key file

   3. **Convert to Base64**:
      ```bash
      base64 -i path/to/your-service-account-key.json | tr -d '\n'
      ```

   4. **Add to Environment**:
      - Copy the base64 string to `GCS_SERVICE_ACCOUNT_KEY_BASE64`
      - Set your bucket name in `GCS_BUCKET_NAME`
      - Set your file name in `GCS_FILE_NAME`

   The application will automatically:
   - ✅ **Use GCS authentication** if service account credentials are provided
   - ✅ **Fallback to direct URL** if GCS credentials are missing
   - ✅ **Show connection status** in the dashboard

   ### Required GCS Permissions

   Your service account needs the following IAM roles:
   - **Storage Object Viewer** (`roles/storage.objectViewer`) on the bucket
   - Or **Storage Legacy Bucket Reader** (`roles/storage.legacyBucketReader`) for basic access

3. **Run Development Server**:
   ```bash
   npm run dev
   ```

4. **Access the Application**:
   Open [http://localhost:3000](http://localhost:3000) in your browser.

## CORS Issue Resolution

This application includes a built-in solution for CORS (Cross-Origin Resource Sharing) issues:

- **Problem**: Direct browser requests to external APIs often fail due to CORS restrictions
- **Solution**: Uses Next.js API routes (`/api/feedback`) as a proxy server
- **How it works**: 
  1. Frontend calls `/api/feedback` (same origin, no CORS issue)
  2. Server-side API route fetches data from external URL
  3. Returns data with proper CORS headers

If you encounter "Failed to fetch" errors, this proxy approach should resolve them automatically.

## Cache-Busting & Fresh Data

The application implements aggressive cache-busting to ensure you always get the latest data:

- **Server-side**: Adds timestamp and random parameters to cloud storage requests
- **Client-side**: Uses cache-busting URLs and no-cache headers
- **HTTP Headers**: Multiple cache-prevention headers (Cache-Control, Pragma, Expires)
- **Dynamic ETags**: Prevents intermediate proxy caching
- **Real-time Timestamps**: Shows exactly when data was last fetched

This ensures that when you click "Refresh", you get the most up-to-date feedback data from your cloud storage, not cached versions.

### Smart 304 Handling

The application intelligently handles HTTP 304 "Not Modified" responses:
- **304 Response**: Indicates the file hasn't changed since last fetch
- **Automatic Retry**: Makes a fresh request without conditional headers
- **Always Fresh**: Ensures you get the current data even when the file hasn't changed

This approach balances efficiency (respecting when files haven't changed) with freshness (always getting the latest data).

## Authentication

- **Username**: `admin_adam_agent`
- **Password**: `admin@adam_Agent123`

## Project Structure

```
src/
├── app/
│   ├── dashboard/          # Dashboard page
│   ├── login/              # Login page
│   ├── layout.tsx          # Root layout
│   └── page.tsx            # Home page (redirects)
├── components/
│   ├── FeedbackDashboard.tsx  # Main dashboard component
│   └── LoginForm.tsx          # Login form component
├── lib/
│   ├── auth.ts             # Authentication utilities
│   └── feedbackService.ts  # Feedback data service
├── types/
│   └── feedback.ts         # TypeScript interfaces
└── middleware.ts           # Route protection middleware
```

## Feedback Data Structure

The application expects feedback data in the following JSON format:

```json
[
  {
    "agent_name": "Adam Setup",
    "user_email": "admin@adsecura.com",
    "partner_name": "partner_b2p",
    "timestamp": "2025-06-19T07:50:08.660231",
    "user_query": "How many line items do I have?",
    "ai_response": "AI response text...",
    "feedback": "User feedback text",
    "sentiment": "positive"
  }
]
```

## Dashboard Features

- **Statistics Overview**: Total feedback count and sentiment breakdown
- **Advanced Filtering**: 
  - Search by query, email, or agent name
  - Filter by sentiment (positive/negative/neutral)
  - **Multi-select email filter** with checkboxes for precise user selection
- **Active Filter Display**: Visual tags showing all applied filters with quick removal
- **Detailed View**: Click on feedback items to see full details
- **Real-time Updates**: Aggressive cache-busting ensures fresh data on every refresh
- **Last Updated Timestamp**: Shows when data was last fetched from the source
- **Responsive Design**: Works on desktop and mobile devices

## Security

- Session-based authentication using HTTP cookies
- Middleware protection for dashboard routes
- Static credentials (suitable for internal admin use)
- Secure cookie settings with SameSite and Secure flags

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```