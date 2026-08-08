import assert from 'node:assert/strict';
import { findAuthConflict, findIdentityConflict, injectIdentity } from '../src/identityGuard.js';

const session = {
  userid: '2227082695389976109',
  employeeId: '805851627118034951',
  email: '0617001@e.cn',
  mobile: '13800000000',
  jobNum: 'RYGH5612',
  account: '0617001@e.cn',
};

assert.equal(findIdentityConflict({ userid: '2227082695389976109' }, session), null);
assert.equal(findIdentityConflict({ userid: 'someone-else' }, session), '.userid');
assert.equal(findIdentityConflict({ useridList: ['2227082695389976109'] }, session), null);
assert.equal(findIdentityConflict({ userid_list: ['2227082695389976109', 'someone-else'] }, session), '.userid_list[1]');
assert.equal(findIdentityConflict({ nested: { user_id: '805851627118034951' } }, session), null);
assert.equal(findIdentityConflict({ nested: [{ account: 'attacker@example.com' }] }, session), 'nested[0].account');
assert.equal(findIdentityConflict({ email: session.email, jobNum: session.jobNum }, session), null);
assert.equal(findIdentityConflict({ jobNumList: ['RYGH5612'] }, session), null);
assert.equal(findIdentityConflict({ jobNumList: ['RYGH5612', 'OTHER001'] }, session), '.jobNumList[1]');
assert.equal(findIdentityConflict({ employeeId: '805851627118034951' }, session), null);
assert.equal(findIdentityConflict({ employee_id: 'someone-else' }, session), '.employee_id');

assert.equal(findAuthConflict({ access_token: 'stolen' }), '拒绝调用：参数 .access_token');
assert.equal(findAuthConflict({ nested: { eteams_token: 'stolen' } }), '拒绝调用：参数 nested.eteams_token');
assert.equal(findAuthConflict({ app_key: 'public-app-key' }), null);

const query = {};
injectIdentity(query, undefined, session, { param: 'userid', enabled: true });
assert.equal(query.userid, session.userid);

const query2 = {};
injectIdentity(query2, { account: session.account }, session, { param: 'userid', enabled: true });
assert.equal(query2.userid, undefined);

console.log('identity guard tests passed');
