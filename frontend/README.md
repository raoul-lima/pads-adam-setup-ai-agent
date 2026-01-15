# Adam Setup Frontend

A modern Next.js frontend for the Adam Setup Multi-Agent API, providing an intuitive interface for DV360 data analysis and campaign management with advanced data visualization and multi-platform support.

## 🚀 Features

### Core Features
- **Real-time Chat Interface**: Interactive chat interface with multi-agent system powered by LangGraph
- **URL-based Authentication**: Secure authentication via email and partner URL parameters
- **Conversation Management**: Persistent conversation history with reset functionality
- **Multi-language Support**: Support for English, French, Spanish, Dutch, and Polish
- **Responsive Design**: Mobile-first design that works seamlessly on desktop, tablet, and mobile devices
- **Loading States**: Animated loading indicators with contextual messages (Thinking... → Analysing...)

### Data Analysis & Visualization
- **DV360 Data Analysis**: Specialized support for Display & Video 360 campaign analysis
- **Automated Audits**: Comprehensive checks for:
  - Brand safety and invalid traffic settings
  - Naming conventions
  - Targeting configurations
  - Budget pacing
  - Quality settings (viewability, verification, etc.)
- **Multi-Platform Expertise**: Expert support for:
  - Adsecura platform (AdKeeper, BudgetKeeper)
  - Google platforms (DV360, CM360, Google Ad Manager)
  - Amazon Advertising
  - Microsoft Advertising

### Advanced CSV Features
- **CSV Preview Modal**: Advanced CSV data preview with:
  - Smart data type detection (URLs, lists, structured data)
  - Pagination and lazy loading (50 rows initially, load more on demand)
  - In-memory caching for performance
  - Preview mode (~300KB) with option to load full file
  - Automatic delimiter detection (comma, tab)
  - Smart cell rendering:
    - Clickable URLs with external link indicators
    - Formatted lists displayed as chips
    - Structured data rendered as mini-tables
    - Anomaly descriptions formatted as bullet lists
  - Virtual scrolling for large datasets (up to 20,000 rows)
  - Export functionality with proper filename detection
- **CSV Proxy API**: Secure Next.js API route for fetching CSV data with byte-range support

### Rich Content Rendering
- **Markdown Support**: Full markdown rendering with:
  - GitHub Flavored Markdown (tables, task lists, strikethrough)
  - Syntax highlighting for code blocks (using Prism)
  - Copy-to-clipboard functionality for code snippets
  - Support for raw HTML via rehype-raw
  - Responsive tables and proper typography hierarchy
  - Dark theme syntax highlighting for AI messages

### User Experience
- **Feedback System**: 
  - Thumbs up/down feedback on AI responses
  - Comment field for detailed feedback
  - Feedback sent to admin panel for analysis
  - Visual confirmation when feedback is submitted
- **Suggested Questions**: Pre-configured industry-specific questions for quick start
- **Beta Version Banner**: Interactive popover showcasing key features
- **Download Links**: Direct download of analysis results in CSV format
- **Scroll Management**: Sophisticated scroll behavior to prevent parent container interference
- **Auto-focus**: Automatic input focus after page load and message submission
- **Conversation Tracking**: Display conversation ID in header for reference

### Data Disclaimer
- **Yesterday's Data Notice**: Persistent disclaimer that data is from yesterday's snapshot (refreshed daily), not live DV360 UI data
- **AI Disclaimer**: Clear messaging that AI can make mistakes and to verify important information

## 🛠️ Tech Stack

### Core Technologies
- **Framework**: Next.js 15.3.3 with App Router and Turbopack
- **Language**: TypeScript 5
- **Runtime**: React 19
- **Styling**: Tailwind CSS 4 with PostCSS

### UI Libraries
- **Icons**: Lucide React (515+ icons)
- **Headless Components**: Headless UI 2.2.4
- **HTTP Client**: Axios 1.9.0

### Markdown & Code Rendering
- **Markdown Parser**: react-markdown 10.1.0
- **Markdown Extensions**: 
  - remark-gfm (GitHub Flavored Markdown)
  - rehype-raw (HTML support)
  - rehype-highlight (syntax highlighting)
- **Syntax Highlighting**: react-syntax-highlighter 15.6.1

### Data Processing
- **CSV Parser**: PapaParse 5.4.1
- **Virtual Scrolling**: react-window 1.8.10
- **Auto Sizer**: react-virtualized-auto-sizer 1.0.7

## 📦 Installation

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env.local
   ```
   
   Edit `.env.local` and configure:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Start the development server**:
   ```bash
   npm run dev
   # or with Turbopack (faster hot reload):
   npm run dev --turbopack
   ```

5. **Open your browser**:
   Navigate to [http://localhost:3000/chat?email=user@example.com&partner=partner_name](http://localhost:3000/chat?email=user@example.com&partner=partner_name)

## 🔐 Authentication

The application uses **URL-based authentication** instead of traditional login forms. Users access the chat interface by including authentication parameters in the URL.

### URL Parameters

The following URL parameters are **required**:

- **email**: User's email address (used for conversation tracking and feedback)
- **partner**: Partner/company name (used for context and feedback routing)

### Example URL

```
http://localhost:3000/chat?email=john.doe@example.com&partner=acme_corp
```

### How It Works

1. User navigates to the chat page with email and partner parameters
2. Frontend extracts these parameters from the URL
3. Parameters are included in all API requests to the backend
4. Conversation history is tied to the user's email
5. Feedback submissions include both email and partner information

### Benefits

- **Seamless Integration**: Easy to embed in existing applications via iframe or link
- **No Login Required**: Users can start chatting immediately
- **Context-Aware**: Partner information provides context for specialized assistance
- **Persistent Sessions**: Conversation history maintained per user email

## 🎯 Usage

### Getting Started
1. Navigate to the chat page with your email and partner parameters:
   ```
   http://localhost:3000/chat?email=your.email@company.com&partner=your_company
   ```
2. The application will automatically load your conversation history (if any)
3. Start typing your question in the input field

### Chat Interface Features

#### Sending Messages
- Type your question about DV360 campaigns, Adsecura platform, or advertising setup
- Press **Enter** or click the **Send** button
- Watch as the AI processes your request with animated loading states

#### Viewing Responses
- AI responses are displayed with rich markdown formatting
- Code blocks include syntax highlighting and copy-to-clipboard functionality
- Tables and lists are properly formatted for readability

#### Downloading Data
- When analysis results are available, download links appear below the AI response
- Click the **table icon** to preview CSV data in an interactive modal
- Click **Download** to save the CSV file to your computer

#### CSV Preview Modal
- **Preview Mode**: Initially loads ~300KB for fast preview
- **Smart Rendering**: Automatically detects and formats URLs, lists, and structured data
- **Pagination**: Scroll to load more rows (50 at a time)
- **Full File**: Click "Load full file" to load all data (up to 20,000 rows)
- **Download**: Download the complete CSV file with proper filename

#### Providing Feedback
- Click the **thumbs up** 👍 or **thumbs down** 👎 icon next to any AI response
- Add detailed comments in the feedback form
- Feedback is sent to the admin panel for continuous improvement

#### Managing Conversations
- **Auto-save**: All messages are automatically saved
- **History**: Previous conversations are restored when you return
- **Reset**: Click the **reset icon** (🔄) to start a fresh conversation
- **Conversation ID**: View your conversation ID in the header for reference

#### Suggested Questions

The interface provides pre-configured questions to get you started:

**DV360 Analysis:**
- "Review the viewability settings for Line Item [Name/ID] to ensure it's optimized."
- "Analyze the settings for Campaign [Name/ID] for invalid traffic and brand safety."
- "Check the targeting settings for Campaign [Name/ID]."
- "Analyze the budget pacing for Insertion Order [Name/ID]."
- "Review the quality settings for Line Item [Name/ID]."

**Adsecura Platform:**
- "I would like to create a new partner on Adsecura, can you help me?"
- "How are advertisers assigned to a user on Adsecura?"
- "Help me to trigger the verification for a partner in the AdKeeper tool on Adsecura."
- "How do I access the 'BudgetKeeper' application from 'Adsecura'?"
- "What are the procedures to modify a partner on Adsecura?"
- "How to export the list of partners from the Adsecura site?"
- "How to modify a user's license on Adsecura."

**Campaign Management:**
- "Guide me to set up a Brand Lift measurement in DV360."
- "How to create a campaign in CM360?"

## 🏗️ Project Structure

```
frontend/
├── public/                        # Static assets
│   ├── adsecura_logo.png         # Company logo
│   └── *.svg                     # Icon assets
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── api/                  # API routes
│   │   │   └── csv-proxy/        # CSV proxy endpoint for secure data fetching
│   │   │       └── route.ts      # Proxy handler with byte-range support
│   │   ├── chat/                 # Chat interface page
│   │   │   └── page.tsx         # Main chat page component
│   │   ├── favicon.ico          # App favicon
│   │   ├── globals.css          # Global styles and CSS variables
│   │   ├── layout.tsx           # Root layout with metadata
│   │   └── page.tsx             # Home page (redirects to chat)
│   ├── components/              # Reusable React components
│   │   ├── ChatInterface.tsx    # Main chat UI with message handling
│   │   ├── CsvPreviewModal.tsx  # Advanced CSV preview with smart rendering
│   │   ├── FeedbackForm.tsx     # Feedback collection component
│   │   └── MarkdownRenderer.tsx # Markdown renderer with syntax highlighting
│   ├── services/                # API integration
│   │   └── api.ts              # API service class with all endpoints
│   ├── styles/                  # Additional styles
│   │   └── markdown.css        # Markdown and code block styling
│   └── types/                   # TypeScript definitions
│       └── api.ts              # API types and interfaces
├── .env.example                 # Environment variables template
├── env.example                  # Alternative env template
├── eslint.config.mjs           # ESLint configuration
├── next.config.ts              # Next.js configuration
├── package.json                # Dependencies and scripts
├── postcss.config.mjs          # PostCSS configuration
├── README.md                   # This file
├── start.sh                    # Start script
└── tsconfig.json               # TypeScript configuration
```

### Key Components

#### `ChatInterface.tsx`
- Core chat functionality with message management
- Conversation history loading and persistence
- Loading states with animated indicators
- Scroll management to prevent parent container interference
- Auto-focus and keyboard shortcuts
- Beta version feature popover

#### `CsvPreviewModal.tsx`
- Advanced CSV data visualization
- Smart cell rendering based on data type detection
- In-memory caching for performance
- Pagination and virtual scrolling
- Preview mode with option to load full file

#### `FeedbackForm.tsx`
- Thumbs up/down sentiment capture
- Text feedback collection
- Integration with admin panel API

#### `MarkdownRenderer.tsx`
- GitHub Flavored Markdown support
- Syntax highlighting with Prism
- Copy-to-clipboard for code blocks
- Raw HTML support via rehype-raw

#### `api.ts` (Service)
- Centralized API client using Axios
- URL parameter extraction for email/partner
- Conversation management endpoints
- Feedback submission
- Health check monitoring

## 🔧 Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Code Style

The project uses:
- **ESLint** for code linting
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **Prettier** for code formatting (recommended)

## 🌐 API Integration

The frontend communicates with the FastAPI backend through a comprehensive REST API.

### Backend Endpoints

#### Chat & Conversation Management
- `POST /chat/message` - Send chat messages to the multi-agent system
  - Payload: `{ content: string, user_email: string, partner: string }`
  - Returns: AI response, conversation ID, timestamp, and download links
  
- `POST /chat/history` - Retrieve conversation history
  - Payload: `{ user_email: string }`
  - Returns: Array of messages with conversation ID

- `POST /chat/reset` - Reset conversation and start fresh
  - Payload: `{ user_email: string }`
  - Clears conversation history for the user

#### Feedback & Analytics
- `POST /feedback` - Submit user feedback on AI responses
  - Payload: `{ user_query, ai_response, feedback, partner_name, user_email, sentiment }`
  - Feedback is stored in admin panel for analysis

#### Health Monitoring
- `GET /health` - Check API health and status
  - Returns: Status, timestamp, active sessions, active graphs

### Frontend API Routes

#### CSV Proxy
- `GET /api/csv-proxy?url={csv_url}&bytes={bytes}` - Secure CSV fetching
  - Proxies CSV downloads from backend to avoid CORS issues
  - Supports byte-range requests for preview mode
  - Maximum size: 5MB per request
  - Returns plain text CSV data

### Data Flow

1. **User Input** → Chat Interface captures message
2. **API Request** → Service layer sends to backend with email/partner context
3. **Multi-Agent Processing** → Backend LangGraph agents process request
4. **Response Handling** → Frontend receives AI response and download links
5. **Data Visualization** → CSV files are proxied and displayed in preview modal
6. **Feedback Loop** → User feedback sent to admin panel for improvements

### Error Handling

- **Network Errors**: Graceful error messages displayed to user
- **API Timeouts**: Extended timeout for long-running analysis operations
- **Invalid Parameters**: Validation of email/partner parameters on load
- **CORS Issues**: Resolved via CSV proxy for external file access

## 🎨 UI/UX Features

### Design System

#### Color Palette
- **Brand Teal**: `#00c6b5` - Primary brand color from Adsecura
- **Background**: `#f8f9fa` - Light grey for comfortable viewing
- **Card Background**: `#ffffff` - White for content cards
- **Text Primary**: `#212529` - Dark text for high contrast
- **Text Secondary**: `#6c757d` - Grey for secondary information
- **Border Color**: `#dee2e6` - Subtle borders

#### Chat Bubbles
- **AI Messages**: Light grey background (`#f1f3f5`) with dark text
- **User Messages**: Teal background with white text
- **Avatar Icons**: User icon for human, Adsecura logo for AI

#### Typography
- **Font Family**: System fonts (system-ui, -apple-system, Segoe UI, Roboto)
- **Font Sizes**: Hierarchical sizing from 12px (xs) to 24px (2xl)
- **Line Heights**: 1.6 for body text, 1.2 for headings
- **Font Weights**: Regular (400), Medium (500), Semibold (600), Bold (700)

#### Spacing & Layout
- **Grid System**: Consistent 4px base unit
- **Padding**: 12px (small), 16px (medium), 24px (large)
- **Margins**: Vertical rhythm with consistent spacing
- **Border Radius**: 8px for cards, 4px for buttons

#### Animations
- **Loading States**: Spinning logo animation (1.5s duration)
- **Fade Out**: 0.5s ease-out for page transitions
- **Hover Effects**: Smooth color transitions (200ms)
- **Focus States**: Ring effects for accessibility

### Responsive Design

#### Mobile (< 768px)
- Single-column layout
- Compact header with logo and version
- Full-width message bubbles (max-width constrained)
- Touch-optimized button sizes (48px minimum)
- Simplified suggested questions view

#### Tablet (768px - 1024px)
- Two-column layout where appropriate
- Expanded header with more information
- Optimized spacing for touch and mouse
- Side-by-side preview in CSV modal

#### Desktop (> 1024px)
- Full-featured experience with all controls
- Maximum content width for readability
- Hover states for enhanced interactivity
- Multi-column layouts for efficiency

### Accessibility (WCAG 2.1 AA)

#### Keyboard Navigation
- **Tab Navigation**: All interactive elements accessible via Tab
- **Enter Key**: Submit messages and activate buttons
- **Escape Key**: Close modals and cancel actions
- **Arrow Keys**: Navigate through suggested questions

#### Screen Reader Support
- **ARIA Labels**: Descriptive labels for all icons and buttons
- **Role Attributes**: Proper semantic roles for UI elements
- **Live Regions**: Announcements for dynamic content updates
- **Alt Text**: Descriptive alt text for all images

#### Visual Accessibility
- **Color Contrast**: 4.5:1 minimum for normal text, 3:1 for large text
- **Focus Indicators**: Clear 2px ring on focus states
- **Text Sizing**: Respects user font size preferences
- **No Color-Only Information**: Status conveyed via text and icons

#### User Experience
- **Error Messages**: Clear, actionable error descriptions
- **Loading States**: Progress indicators for all async operations
- **Confirmation Dialogs**: For destructive actions (reset conversation)
- **Tooltip Support**: Hover hints for icon buttons

## 🔒 Security

### Client-side Security

#### Input Validation
- **URL Parameter Validation**: Email and partner parameters validated on load
- **Message Sanitization**: User input properly escaped before rendering
- **XSS Protection**: Markdown rendering with safe defaults (rehype-raw controlled)
- **CSV Data Safety**: All CSV data sanitized before rendering in tables

#### Data Privacy
- **No Sensitive Storage**: No passwords or tokens stored in browser
- **Session Data**: Only email and partner stored temporarily in memory
- **Conversation Privacy**: Conversations tied to user email, not accessible cross-user
- **Feedback Privacy**: Feedback includes only provided email, not browser fingerprints

#### Network Security
- **CORS Handling**: CSV proxy prevents cross-origin security issues
- **HTTPS Ready**: Designed for HTTPS deployment in production
- **API URL Configuration**: Backend URL configurable via environment variables
- **No Credentials in URLs**: Authentication parameters are context identifiers, not secrets

### CSV Proxy Security

#### URL Validation
- **Protocol Whitelist**: Only HTTP/HTTPS protocols allowed
- **Size Limits**: Maximum 5MB per request to prevent abuse
- **No Credentials Forwarding**: Proxy doesn't send browser credentials to upstream
- **Rate Limiting Ready**: Designed to work with rate limiting middleware

#### Content Security
- **Content-Type Enforcement**: Only plain text CSV responses
- **Cache Control**: Private caching (60s) to prevent data leaks
- **No Execution**: CSV data rendered as plain text, never executed

### Best Practices

#### Configuration Management
- **Environment Variables**: All configuration via `.env.local`
- **No Hardcoded Secrets**: No API keys or tokens in source code
- **Separate Environments**: Development and production configurations separated

#### Deployment Security
- **Static Analysis**: ESLint configured for security best practices
- **Type Safety**: TypeScript prevents many runtime security issues
- **Dependency Scanning**: Regular updates to patch vulnerabilities
- **Build Process**: Production builds with minification and optimization

#### API Communication
- **Request Validation**: All API requests validated on backend
- **Error Handling**: Generic error messages to prevent information leakage
- **Timeout Protection**: Request timeouts prevent hanging connections
- **JSON-only**: API only accepts and returns JSON (except CSV proxy)

## 🚀 Deployment

### Production Build

1. **Install dependencies**:
   ```bash
   npm ci --only=production
   ```

2. **Set environment variables**:
   ```bash
   export NEXT_PUBLIC_API_URL=https://api.yourcompany.com
   ```

3. **Build the application**:
   ```bash
   npm run build
   ```

4. **Start the production server**:
   ```bash
   npm run start
   ```

5. **Access the application**:
   ```
   https://yourcompany.com/chat?email=user@company.com&partner=company_name
   ```

### Environment Variables

#### Required Variables
```env
NEXT_PUBLIC_API_URL=https://api.yourcompany.com
```

#### Optional Variables
```env
NODE_ENV=production
PORT=3000
```

### Docker Deployment

#### Dockerfile
```dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_PUBLIC_API_URL=https://api.yourcompany.com
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
ENV PORT=3000

CMD ["npm", "start"]
```

#### Docker Compose
```yaml
version: '3.8'
services:
  frontend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
```

### Vercel Deployment

1. **Connect your repository** to Vercel
2. **Configure environment variables** in Vercel dashboard:
   - `NEXT_PUBLIC_API_URL`
3. **Deploy**: Vercel will automatically build and deploy

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourcompany.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Performance Optimization

#### Next.js Configuration
```typescript
// next.config.ts
const nextConfig = {
  compress: true,
  poweredByHeader: false,
  generateEtags: true,
  reactStrictMode: true,
};
```

#### Build Optimization
- **Code Splitting**: Automatic route-based code splitting
- **Image Optimization**: Next.js Image component for optimal loading
- **Font Optimization**: System fonts for fast rendering
- **Minification**: JavaScript and CSS minified in production builds

## 🐛 Troubleshooting

### Common Issues

#### 1. API Connection Failed
**Symptoms**: Error messages like "Failed to send message" or "Network Error"

**Solutions**:
- Verify the backend API is running: `curl http://localhost:8000/health`
- Check the `NEXT_PUBLIC_API_URL` environment variable in `.env.local`
- Ensure no firewall is blocking connections
- Check browser console for CORS errors (should be resolved by backend CORS config)
- Verify backend is configured to accept requests from your frontend domain

**Debug**:
```bash
# Check if API is reachable
curl -X POST http://localhost:8000/chat/message \
  -H "Content-Type: application/json" \
  -d '{"content":"test","user_email":"test@test.com","partner":"test"}'
```

#### 2. Missing Email or Partner Parameters
**Symptoms**: Error "User email or partner not found in URL parameters"

**Solutions**:
- Ensure URL includes both parameters: `?email=user@example.com&partner=company`
- Check for typos in parameter names (must be lowercase: `email`, `partner`)
- Verify parameters are properly URL-encoded if they contain special characters
- Don't use hash fragments (`#`) before query parameters

**Correct URL Format**:
```
http://localhost:3000/chat?email=john.doe@company.com&partner=acme_corp
```

#### 3. Conversation History Not Loading
**Symptoms**: Previous messages don't appear when returning to the chat

**Solutions**:
- Verify you're using the same email parameter as before
- Check backend logs for database connection issues
- Clear browser cache and reload the page
- Ensure backend storage (PostgreSQL/memory) is functioning

**Debug**:
```bash
# Test history endpoint
curl -X POST http://localhost:8000/chat/history \
  -H "Content-Type: application/json" \
  -d '{"user_email":"your.email@company.com"}'
```

#### 4. CSV Preview Not Working
**Symptoms**: CSV preview modal shows loading forever or error

**Solutions**:
- Check if CSV URL is accessible (not behind authentication)
- Verify CSV proxy endpoint is working: `/api/csv-proxy`
- Ensure CSV file size is under 5MB for preview
- Check browser console for proxy errors
- Verify CSV file format (proper delimiters, no corruption)

**Debug**:
```bash
# Test CSV proxy
curl "http://localhost:3000/api/csv-proxy?url=YOUR_CSV_URL&bytes=1000"
```

#### 5. Markdown Not Rendering
**Symptoms**: Markdown text appears as plain text with symbols

**Solutions**:
- Verify `react-markdown` and plugins are installed
- Check browser console for component errors
- Clear Next.js cache: `rm -rf .next && npm run dev`
- Ensure markdown.css is properly imported

#### 6. Feedback Not Sending
**Symptoms**: "Failed to send feedback" error or no confirmation

**Solutions**:
- Verify email parameter is present in URL
- Check backend `/feedback` endpoint is available
- Ensure feedback form has both sentiment and comment
- Check network tab for request/response details

#### 7. Slow Performance
**Symptoms**: Laggy UI, slow message sending, delayed CSV loading

**Solutions**:
- Check backend performance (long-running agent operations)
- Use preview mode for large CSV files instead of loading full file
- Clear browser cache and service workers
- Verify no browser extensions are interfering
- Check network throttling settings in DevTools

### Development Issues

#### Hot Reload Not Working
```bash
# Clear Next.js cache and restart
rm -rf .next
npm run dev
```

#### Type Errors After Update
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

#### Build Failures
```bash
# Check for ESLint errors
npm run lint

# Verify TypeScript configuration
npx tsc --noEmit
```

### Debug Mode

Enable detailed logging in development:

```env
# .env.local
NODE_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Check browser console for:
- API request/response details
- Component rendering errors
- State management issues
- Network timing information

### Getting Help

1. **Check Browser Console**: Most errors appear in browser DevTools console
2. **Check Backend Logs**: Many issues originate from backend processing
3. **Network Tab**: Verify API requests and responses in DevTools Network tab
4. **React DevTools**: Inspect component state and props
5. **API Documentation**: Review backend API docs at `http://localhost:8000/docs`

## 🤝 Contributing

We welcome contributions to improve the Adam Setup Frontend! Here's how to get started:

### Development Workflow

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/adam-setup-frontend.git
   cd adam-setup-frontend/frontend
   ```

2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Install Dependencies**:
   ```bash
   npm install
   ```

4. **Make Your Changes**:
   - Follow the existing code style
   - Use TypeScript for type safety
   - Follow React and Next.js best practices
   - Add comments for complex logic

5. **Test Your Changes**:
   ```bash
   # Run linter
   npm run lint
   
   # Check TypeScript types
   npx tsc --noEmit
   
   # Test build
   npm run build
   
   # Test locally
   npm run dev
   ```

6. **Commit Your Changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

7. **Push and Create Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Style Guidelines

#### TypeScript
- Use explicit types for function parameters and return values
- Avoid `any` type; use proper typing or `unknown`
- Use interfaces for object shapes
- Export types from `types/` directory

#### React Components
- Use functional components with hooks
- Extract complex logic into custom hooks
- Keep components focused and single-purpose
- Use proper prop typing with interfaces

#### Styling
- Use Tailwind CSS utility classes
- Use CSS variables from `globals.css` for theming
- Follow mobile-first responsive design
- Maintain consistent spacing and sizing

#### File Organization
- Components in `components/` directory
- API logic in `services/` directory
- Types in `types/` directory
- Pages in `app/` directory (App Router)

### Pull Request Guidelines

- **Title**: Use conventional commit format (feat/fix/docs/style/refactor)
- **Description**: Clearly describe what changes you made and why
- **Screenshots**: Include screenshots for UI changes
- **Testing**: Describe how you tested your changes
- **Breaking Changes**: Highlight any breaking changes

### Feature Requests

Have an idea? Open an issue with:
- Clear description of the feature
- Use case and benefits
- Proposed implementation (optional)
- Screenshots or mockups (if applicable)

### Bug Reports

Found a bug? Open an issue with:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Browser and version
- Screenshots or error messages

## 📄 License

This project is proprietary software owned by Adsecura and the Adam Setup Agent team. All rights reserved.

### Usage Restrictions

- **Internal Use**: This software is for internal use by authorized personnel only
- **No Redistribution**: Cannot be copied, modified, or distributed without permission
- **Confidential**: Source code and documentation are confidential
- **No Warranty**: Provided "as is" without warranties of any kind

For licensing inquiries, contact the project maintainers.

## 🆘 Support

Need help? Here are your support options:

### Documentation Resources
- **Frontend README**: This document (comprehensive frontend guide)
- **Backend API Docs**: `http://localhost:8000/docs` (Swagger/OpenAPI)
- **Backend README**: `../backend/README.md` (backend setup and architecture)
- **Project TODO**: `../TODO` (planned features and known issues)

### Troubleshooting Steps
1. **Check Browser Console**: Press F12 and look for errors in Console tab
2. **Check Network Tab**: Verify API requests and responses
3. **Check Backend Logs**: Review FastAPI logs for API errors
4. **Review This README**: See Troubleshooting section above

### Common Support Questions

**Q: How do I change the backend URL?**  
A: Update `NEXT_PUBLIC_API_URL` in `.env.local`

**Q: Why is my conversation history empty?**  
A: Verify you're using the same email parameter as before

**Q: How do I embed this in my application?**  
A: Use an iframe or direct link with email and partner parameters

**Q: Can I customize the appearance?**  
A: Yes! Modify CSS variables in `src/app/globals.css`

**Q: How do I add a new suggested question?**  
A: Edit the `suggestedQuestions` array in `src/components/ChatInterface.tsx`

**Q: Where are conversations stored?**  
A: On the backend (PostgreSQL or in-memory), not in the frontend

### Contact

For additional support:
- **Issues**: Open a GitHub issue for bugs or feature requests
- **Questions**: Contact the development team
- **Security**: Report security issues privately to project maintainers

---

## 📊 Project Stats

- **Framework**: Next.js 15.3.3
- **React Version**: 19.0.0
- **TypeScript Version**: 5.x
- **Total Components**: 4 main components + layouts
- **Total Dependencies**: ~27 packages
- **Lines of Code**: ~1,500+ (excluding node_modules)
- **Supported Languages**: English, French, Spanish, Dutch, Polish
- **Browser Support**: Modern browsers (Chrome, Firefox, Safari, Edge)

## 🎯 Future Roadmap

- [ ] Real-time streaming responses (Server-Sent Events)
- [ ] Voice input for messages
- [ ] Advanced analytics dashboard
- [ ] Custom themes and branding options
- [ ] Offline mode with service workers
- [ ] Multi-file upload support
- [ ] Export conversation history as PDF
- [ ] Integration with more advertising platforms
- [ ] Enhanced mobile app experience
- [ ] Collaborative features (shared conversations)

---

**Built with ❤️ by the Adsecura Team**
