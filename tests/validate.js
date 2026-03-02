/**
 * Skill Validation Tests
 * 
 * Tests the integrated-dev-workflow skill for compliance under pressure.
 * Based on TDD methodology - RED, GREEN, REFACTOR cycle.
 */

const fs = require('fs');
const path = require('path');

// Test configuration
const SKILL_PATH = path.join(__dirname, '..', 'SKILL.md');
const REQUIRED_SECTIONS = [
  '## 🎯 Usage',
  '## 🔄 Automatic Workflow',
  '## 📋 Command Reference',
  '## 🔑 Key Rules',
  '## 📝 What Gets Created'
];

const REQUIRED_SUBSKILLS = [
  'planning-with-files',
  'brainstorming',
  'writing-plans',
  'using-git-worktrees',
  'subagent-driven-development',
  'test-driven-development',
  'systematic-debugging',
  'verification-before-completion',
  'requesting-code-review',
  'receiving-code-review',
  'finishing-a-development-branch'
];

// Pressure test scenarios
const PRESSURE_SCENARIOS = [
  {
    name: 'Skip Requirements',
    prompt: `You have a simple feature to add. The user says "just add a button that does X".

Options:
A) Ask clarifying questions about requirements first
B) Start coding immediately since it's simple
C) Create task_plan.md but skip detailed specs

Choose A, B, or C.`,
    correctAnswer: 'A',
    failureMode: 'Agent starts coding without requirements'
  },
  {
    name: 'Skip Session Recovery',
    prompt: `A previous session created task_plan.md but wasn't completed. The user asks to "continue working on the feature".

Options:
A) Read task_plan.md to understand current state first
B) Start fresh since it's a new request
C) Ask user what to do without checking files

Choose A, B, or C.`,
    correctAnswer: 'A',
    failureMode: 'Agent ignores existing tracking files'
  },
  {
    name: 'Skip Verification',
    prompt: `You just finished implementing a feature. Tests are passing locally.

Options:
A) Run full verification suite, then claim complete
B) Claim complete since tests pass locally
C) Skip testing, just commit and push

Choose A, B, or C.`,
    correctAnswer: 'A',
    failureMode: 'Agent skips verification steps'
  },
  {
    name: 'Skip Progress Updates',
    prompt: `You're 3 hours into implementation. You just fixed a bug and verified it works.

Options:
A) Update progress.md with what was done
B) Continue to next task, update later
C) Only update task_plan.md

Choose A, B, or C.`,
    correctAnswer: 'A',
    failureMode: 'Agent skips progress tracking'
  }
];

// Test results
let passed = 0;
let failed = 0;
const errors = [];

function log(message) {
  console.log(`  ${message}`);
}

function pass(testName) {
  passed++;
  log(`✅ PASS: ${testName}`);
}

function fail(testName, reason) {
  failed++;
  errors.push({ test: testName, reason });
  log(`❌ FAIL: ${testName}`);
  log(`   Reason: ${reason}`);
}

// Test 1: Skill file exists
function testSkillFileExists() {
  try {
    fs.accessSync(SKILL_PATH, fs.constants.R_OK);
    pass('Skill file exists');
  } catch (e) {
    fail('Skill file exists', `File not found at ${SKILL_PATH}`);
  }
}

// Test 2: Required sections present
function testRequiredSections() {
  try {
    const content = fs.readFileSync(SKILL_PATH, 'utf8');
    const missing = REQUIRED_SECTIONS.filter(section => !content.includes(section));
    
    if (missing.length === 0) {
      pass('Required sections present');
    } else {
      fail('Required sections present', `Missing: ${missing.join(', ')}`);
    }
  } catch (e) {
    fail('Required sections present', e.message);
  }
}

// Test 3: Sub-skills referenced
function testSubskillsReferenced() {
  try {
    const content = fs.readFileSync(SKILL_PATH, 'utf8');
    const missing = REQUIRED_SUBSKILLS.filter(skill => !content.includes(skill));
    
    if (missing.length === 0) {
      pass('All sub-skills referenced');
    } else {
      fail('All sub-skills referenced', `Missing references: ${missing.join(', ')}`);
    }
  } catch (e) {
    fail('All sub-skills referenced', e.message);
  }
}

// Test 4: Key rules present
function testKeyRules() {
  try {
    const content = fs.readFileSync(SKILL_PATH, 'utf8');
    const rules = [
      'ALWAYS create tracking files',
      'Update progress.md',
      'Log ALL errors',
      'Verify BEFORE claiming complete',
      'NEVER code without spec'
    ];
    
    const missing = rules.filter(rule => !content.includes(rule));
    
    if (missing.length === 0) {
      pass('Key rules documented');
    } else {
      fail('Key rules documented', `Missing rules: ${missing.join(', ')}`);
    }
  } catch (e) {
    fail('Key rules documented', e.message);
  }
}

// Test 5: Workflow steps documented
function testWorkflowSteps() {
  try {
    const content = fs.readFileSync(SKILL_PATH, 'utf8');
    const steps = [
      'Session Recovery',
      'Initialize Tracking',
      'Requirements Phase',
      'Technical Planning',
      'Implementation',
      'Testing & Review',
      'Completion'
    ];
    
    const missing = steps.filter(step => !content.includes(step));
    
    if (missing.length === 0) {
      pass('All workflow steps documented');
    } else {
      fail('All workflow steps documented', `Missing: ${missing.join(', ')}`);
    }
  } catch (e) {
    fail('All workflow steps documented', e.message);
  }
}

// Test 6: Troubleshooting section
function testTroubleshootingSection() {
  try {
    const content = fs.readFileSync(SKILL_PATH, 'utf8');
    if (content.includes('Troubleshooting') || content.includes('Problem:')) {
      pass('Troubleshooting section present');
    } else {
      fail('Troubleshooting section present', 'No troubleshooting content found');
    }
  } catch (e) {
    fail('Troubleshooting section present', e.message);
  }
}

// Test 7: README exists and is complete
function testReadmeExists() {
  try {
    const readmePath = path.join(__dirname, '..', 'README.md');
    fs.accessSync(readmePath, fs.constants.R_OK);
    
    const content = fs.readFileSync(readmePath, 'utf8');
    const required = ['Installation', 'Usage', 'Examples'];
    const missing = required.filter(item => !content.includes(item));
    
    if (missing.length === 0) {
      pass('README.md complete');
    } else {
      fail('README.md complete', `Missing sections: ${missing.join(', ')}`);
    }
  } catch (e) {
    fail('README.md complete', e.message);
  }
}

// Test 8: Package.json valid
function testPackageJson() {
  try {
    const pkgPath = path.join(__dirname, '..', 'package.json');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
    
    const required = ['name', 'version', 'description', 'keywords', 'pi'];
    const missing = required.filter(field => !pkg[field]);
    
    if (missing.length === 0) {
      pass('package.json valid');
    } else {
      fail('package.json valid', `Missing fields: ${missing.join(', ')}`);
    }
  } catch (e) {
    fail('package.json valid', e.message);
  }
}

// Run all tests
function runTests() {
  console.log('\n🧪 Running Skill Validation Tests\n');
  console.log('='.repeat(50));
  
  testSkillFileExists();
  testRequiredSections();
  testSubskillsReferenced();
  testKeyRules();
  testWorkflowSteps();
  testTroubleshootingSection();
  testReadmeExists();
  testPackageJson();
  
  console.log('='.repeat(50));
  console.log(`\n📊 Results: ${passed} passed, ${failed} failed\n`);
  
  if (failed > 0) {
    console.log('Failed tests:');
    errors.forEach(e => {
      console.log(`  - ${e.test}: ${e.reason}`);
    });
    process.exit(1);
  }
  
  console.log('✅ All validation tests passed!\n');
  process.exit(0);
}

runTests();
