use serde::{Deserialize, Serialize};
use std::io::{self, Read};

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Intent {
    pub asset: String,
    pub amount_atomic: u64,
    pub destination: String,
    pub network_constraints: Vec<String>,
    pub requester: String,
    pub hourly_limit_override: Option<u64>,
}

#[derive(Debug, Serialize)]
pub struct ApprovalToken {
    pub approved: bool,
    pub reason: String,
    pub token_hash: String,
    pub expires_unix: u64,
}

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).ok();
    let intent: Intent = serde_json::from_str(&input).unwrap_or_else(|_| Intent {
        asset: "ZEPH".into(), amount_atomic: 0, destination: "".into(),
        network_constraints: vec![], requester: "unknown".into(), hourly_limit_override: None,
    });

    let limit = intent.hourly_limit_override.unwrap_or(500_000_000);
    let approved = intent.amount_atomic <= limit
        && intent.network_constraints.iter().any(|c| c.contains("tor") || c.contains("onion"));

    let result = if approved {
        ApprovalToken { approved: true, reason: "OK".into(), token_hash: format!("zdos-{:x}", intent.amount_atomic), expires_unix: 0 }
    } else {
        ApprovalToken { approved: false, reason: "Policy denied".into(), token_hash: "".into(), expires_unix: 0 }
    };
    println!("{}", serde_json::to_string(&result).unwrap());
}
