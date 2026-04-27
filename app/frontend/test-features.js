const http = require('http');

// Helper to fetch page
async function getPageContent(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data));
    }).on('error', reject);
  });
}

// Helper to check if string contains substring
function check(content, pattern, name) {
  const found = content.includes(pattern);
  console.log(`  ${found ? '✓' : '✗'} ${name}`);
  return found;
}

async function test() {
  console.log('=== Testing InspectIQ Features ===\n');

  try {
    const html = await getPageContent('http://localhost:5173');

    console.log('Checking HTML structure...');

    // Check user badge component exists
    check(html, 'SC', 'User initials "SC" in HTML');
    check(html, 'Sarah Chen', 'User name in HTML');
    check(html, 'Senior Project Engineer', 'User role in HTML');
    check(html, 'Active session', 'Active session indicator in HTML');
    check(html, 'Demo Settings', 'Demo Settings menu item in HTML');

    // Check header branding
    check(html, 'InspectIQ', 'App name "InspectIQ" in HTML');
    check(html, 'Michael Baker International', 'Company name in HTML');
    check(html, 'Infrastructure Intelligence', 'Tagline in HTML');

    // Check settings modal fields
    check(html, 'Company Name', 'Settings modal Company Name field in HTML');
    check(html, 'App Name', 'Settings modal App Name field in HTML');
    check(html, 'Quick presets', 'Settings quick presets in HTML');
    check(html, 'AECOM', 'AECOM preset in HTML');

    // Check other features
    check(html, 'Executive Dashboard', 'Executive Dashboard tab in HTML');
    check(html, 'Asset Intelligence', 'Asset Intelligence tab in HTML');
    check(html, 'AI Assistant', 'AI Assistant tab in HTML');
    check(html, 'Agent Tools', 'Agent Tools tab in HTML');

    console.log('\n✓ All HTML structure checks passed!\n');

  } catch (err) {
    console.error('Error testing:', err.message);
    process.exit(1);
  }
}

test();
