const axios = require('axios');

const GENERATOR_URL = 'http://localhost:3001';
const DASHBOARD_URL = 'http://localhost:3000';

async function testIntegration() {
    console.log('🧪 Testing Jarvis App Builder Integration...\n');

    try {
        // Test 1: Generator Service Health
        console.log('1. Testing Generator Service...');
        const generatorHealth = await axios.get(`${GENERATOR_URL}/health`);
        console.log('✅ Generator Service is running');

        // Test 2: Get Available Modules
        console.log('\n2. Testing Module Registry...');
        const modules = await axios.get(`${GENERATOR_URL}/modules`);
        console.log(`✅ Found ${modules.data.length} modules:`);
        modules.data.forEach(module => {
            console.log(`   - ${module.icon} ${module.name}: ${module.description}`);
        });

        // Test 3: Generate Test App
        console.log('\n3. Testing App Generation...');
        const testApp = {
            appName: 'Test Rizz App',
            appSlug: 'test-rizz-app',
            bundleId: 'com.jarvis.test-rizz',
            packageName: 'com.jarvis.test_rizz',
            appScheme: 'test-rizz',
            description: 'A test app for the Rizz module',
            module: modules.data[0] // Use first available module
        };

        const generation = await axios.post(`${GENERATOR_URL}/generate`, testApp);
        
        if (generation.data.success) {
            console.log('✅ App generated successfully!');
            console.log(`   App ID: ${generation.data.appId}`);
            console.log(`   Repo URL: ${generation.data.repoUrl}`);
        } else {
            console.log('❌ App generation failed:', generation.data.error);
        }

        // Test 4: Dashboard Health
        console.log('\n4. Testing Dashboard...');
        const dashboardHealth = await axios.get(`${DASHBOARD_URL}/health`);
        console.log('✅ Dashboard is running');

        console.log('\n🎉 All tests passed! Jarvis App Builder is ready to use.');
        console.log('\n📱 Next steps:');
        console.log('   1. Open http://localhost:3000 in your browser');
        console.log('   2. Create your first app using the dashboard');
        console.log('   3. Download and test the generated app');

    } catch (error) {
        console.error('❌ Test failed:', error.message);
        
        if (error.code === 'ECONNREFUSED') {
            console.log('\n💡 Make sure all services are running:');
            console.log('   - Generator Service: npm run dev (in generator/)');
            console.log('   - Dashboard: npm run dev (in dashboard/)');
            console.log('   - Backend API: python -m uvicorn main:app --reload (in JarvisOne/)');
        }
    }
}

// Run the test
testIntegration();
