import { Storage } from '@google-cloud/storage';

interface GCSConfig {
  bucketName: string;
  fileName: string;
  serviceAccountKeyBase64: string;
}

/**
 * Creates an authenticated Google Cloud Storage client
 */
function createGCSClient(serviceAccountKeyBase64: string): Storage {
  if (!serviceAccountKeyBase64) {
    throw new Error('GCS_SERVICE_ACCOUNT_KEY_BASE64 environment variable is required');
  }

  try {
    // Decode the base64 service account key
    const serviceAccountKeyJson = Buffer.from(serviceAccountKeyBase64, 'base64').toString('utf-8');
    const serviceAccountKey = JSON.parse(serviceAccountKeyJson);

    // Create and return the authenticated storage client
    return new Storage({
      credentials: serviceAccountKey,
      projectId: serviceAccountKey.project_id,
    });
  } catch (error) {
    throw new Error(`Failed to create GCS client: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

interface GCSFetchResult {
  data: unknown;
  metadata: {
    size?: number;
    lastModified?: string;
    etag?: string;
    contentType?: string;
  };
}

/**
 * Fetches a file from Google Cloud Storage using service account authentication
 */
export async function fetchFromGCS(config: GCSConfig): Promise<GCSFetchResult> {
  const { bucketName, fileName, serviceAccountKeyBase64 } = config;

  try {
    console.log(`🔄 Fetching ${fileName} from GCS bucket: ${bucketName}`);

    // Create authenticated storage client
    const storage = createGCSClient(serviceAccountKeyBase64);

    // Get the bucket and file
    const bucket = storage.bucket(bucketName);
    const file = bucket.file(fileName);

    // Check if file exists
    const [exists] = await file.exists();
    if (!exists) {
      throw new Error(`File ${fileName} does not exist in bucket ${bucketName}`);
    }

    // Download the file content
    const [fileContent] = await file.download();
    
    // Parse JSON content
    const jsonData = JSON.parse(fileContent.toString('utf-8'));
    
    // Get file metadata
    const [metadata] = await file.getMetadata();
    
    console.log(`✅ Successfully fetched ${fileName} from GCS`);
    console.log(`📊 File size: ${metadata.size} bytes`);
    console.log(`🕒 Last modified: ${metadata.updated}`);
    console.log(`🏷️ ETag: ${metadata.etag}`);

    return {
      data: jsonData,
      metadata: {
        size: typeof metadata.size === 'string' ? parseInt(metadata.size, 10) : metadata.size,
        lastModified: metadata.updated,
        etag: metadata.etag,
        contentType: metadata.contentType,
      }
    };
  } catch (error) {
    console.error(`❌ Error fetching from GCS:`, error);
    throw new Error(`GCS fetch failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Test GCS connection and permissions
 */
export async function testGCSConnection(config: GCSConfig): Promise<boolean> {
  try {
    const { bucketName, serviceAccountKeyBase64 } = config;
    
    const storage = createGCSClient(serviceAccountKeyBase64);
    const bucket = storage.bucket(bucketName);
    
    // Test bucket access
    const [exists] = await bucket.exists();
    if (!exists) {
      console.error(`❌ Bucket ${bucketName} does not exist or is not accessible`);
      return false;
    }

    console.log(`✅ GCS connection test successful for bucket: ${bucketName}`);
    return true;
  } catch (error) {
    console.error(`❌ GCS connection test failed:`, error);
    return false;
  }
}
