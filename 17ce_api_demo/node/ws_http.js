#!/usr/bin/node

const WebSocket = require('ws')
const crypto = require('crypto')

// 账号密码
const user = 'test@17ce.com'
const api_pwd = '1111111111111'

let ut = parseInt(Date.now()/1000)
let code = md5(Buffer.from(md5(api_pwd).substr(4,19)+user+ut).toString('base64'))
let origin = 'https://wsapi.17ce.com:8001/socket/?ut='+ut+'&code='+code+'&user='+user
let ws = new WebSocket('wss://wsapi.17ce.com:8001/socket',   { origin: origin})

var txnid = 1


var pingInterval = null;
var login = false;
ws.on('open', function open() {
	console.log('connected ok', origin)
	pingInterval = setInterval(function ping() {
		if(!ws) {
			if(pingInterval){
				clearInterval(pingInterval);
				pingInterval = null;
			}
			return;
		}
		ws.ping(noop);
	}, 30*1000);
})

ws.on('close', function close() {
	console.log('disconnected');
	ws = null
})


ws.on('message', function incoming(data) {
	console.log('receive', data);
	var d = "string" == typeof(data) ? JSON.parse(data) : data;
	if(login == false && d['rt'] == 1){
		login = true;
		send_tx();
		return
	}
})
ws.on('error', function errer(err) {
	console.log(err);
	ws = null
})



function  send_tx(){
	if(!ws) return;
	let test = {txnid: txnid, nodetype: [1,2],  num: 1,  Url: "http://www.baidu.com/", TestType: 'HTTP', Host: 'baidu.com', TimeOut: 20, Request: "GET", NoCache: true, Speed: 0, Cookie: '', Trace:false, Referer: 'http://www.baidu.com/', UserAgent: "curl/7.47.0",  FollowLocation: 2, GetMD5: true, GetResponseHeader: true,  MaxDown:  1024*1024, AutoDecompress: true}
	test['type'] = 1;
	test['isps'] = [1,2];
	test['pro_ids'] = '221,49';
	// test['city_ids'] = '280,202,262,246';
	test['areas'] = [1];
	//test['SrcIP'] = '115.239.210.27';
	test['PingSize'] = 32;
	test['PingCount'] = 10;
	//test['SrcIP'] = 'www.baidu.com';
	console.log('send', test)
	ws.send(JSON.stringify(test))
	txnid++;
	setTimeout(send_tx, 60*1000)
}

function noop() {}

function md5 (text) {
	return crypto.createHash('md5').update(text).digest('hex')
}
