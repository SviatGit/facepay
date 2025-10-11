let capturedImageData = null;
let faceVerified = false;

// Start webcam streams on both videos
async function startWebcam(videoId) {
  const video = document.getElementById(videoId);
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    video.srcObject = stream;
  } catch (error) {
    console.error("Error accessing webcam:", error);
    alert("Could not access webcam. Please check permissions.");
  }
}

startWebcam("reg_video");
startWebcam("pay_video");

// Switch tabs
function showTab(tabId) {
  document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
  document.getElementById(tabId).classList.add("active");

  // Reset payment tab UI when switching
  if (tabId === 'payment') {
    resetPaymentUI();
  }
}

// Capture face image from video, returns true if successful, false if not
function captureFace(context) {
  const video = document.getElementById(context === 'register' ? 'reg_video' : 'pay_video');

  if (!video || video.readyState < 2) { // HAVE_CURRENT_DATA
    const statusId = context === 'register' ? "reg_status" : "pay_status";
    document.getElementById(statusId).textContent = "❌ Video stream not ready. Please wait.";
    return false;
  }

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  capturedImageData = canvas.toDataURL("image/jpeg");
  if (context === 'register') {
  document.getElementById("reg_status").textContent = "✅ Face captured successfully!";
  }
  return true;
}

// Register user API call
async function registerUser() {
  const name = document.getElementById("reg_name").value.trim();
  const stripeId = document.getElementById("reg_stripe_id").value.trim();
  const status = document.getElementById("reg_status");

  if (!name || !stripeId) {
    status.textContent = "❌ Please fill in all fields.";
    return;
  }

  if (!captureFace('register')) {
    status.textContent = "❌ Cannot capture face. Please try again.";
    return;
  }

  status.textContent = "Registering...";
  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, stripe_id: stripeId, image_data: capturedImageData }),
    });

    const result = await res.json();
    if (result.status === "success") {
      status.textContent = "✅ Registered successfully!";
    } else {
      status.textContent = "❌ " + (result.error || "Registration failed.");
    }
  } catch (error) {
    status.textContent = "❌ Registration error.";
    console.error("Register error:", error);
  }
}

// Verify face API call (on Verify Face button)
async function verifyFace() {
  const verificationStatus = document.getElementById("face_verification_status");
  verificationStatus.textContent = "";
  faceVerified = false;

  if (!captureFace('payment')) {
    verificationStatus.textContent = "❌ Cannot capture face. Please try again.";
    updateSendButton(false);
    return;
  }

  verificationStatus.textContent = "Verifying face...";

  try {
    const res = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_data: capturedImageData }),
    });
    const result = await res.json();

    if (result.status === "success") {
      faceVerified = true;
      verificationStatus.textContent = "✅ Face verified successfully!";
      updateSendButton(true);
    } else {
      verificationStatus.textContent = "❌ Face not recognized. Please try again.";
      updateSendButton(false);
    }
  } catch (error) {
    verificationStatus.textContent = "❌ Verification error.";
    console.error("Verification error:", error);
    updateSendButton(false);
  }
}

// Enable or disable Send Payment button
function updateSendButton(enabled) {
  document.getElementById("send_payment_btn").disabled = !enabled;
}

// Send payment API call (only allowed if faceVerified === true)
async function sendPayment() {
  const recipientId = document.getElementById("recipient_id").value.trim();
  const amount = parseFloat(document.getElementById("amount").value);
  const faceStatus = document.getElementById("face_verification_status");
  const paymentStatus = document.getElementById("payment_result");

  paymentStatus.textContent = "";

  if (!faceVerified) {
    paymentStatus.textContent = "❌ Please verify your face before sending payment.";
    return;
  }

  if (!recipientId || isNaN(amount) || amount <= 0) {
    paymentStatus.textContent = "❌ Please enter valid recipient and amount.";
    return;
  }

  if (!capturedImageData) {
    paymentStatus.textContent = "❌ No face image available. Please verify face again.";
    updateSendButton(false);
    return;
  }

  paymentStatus.textContent = "Processing payment...";

  try {
    const res = await fetch("/api/pay", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recipient_id: recipientId,
        amount,
        image_data: capturedImageData,
      }),
    });

    let result;
    try {
      result = await res.json();
    } catch (e) {
      throw new Error("Invalid response from server.");
    }

    if (res.ok && result.status === "success") {
      paymentStatus.textContent = "✅ Payment sent! Charge ID: " + result.charge_id;
      paymentStatus.scrollIntoView({ behavior: "smooth" }); // 👈 scroll here
      faceStatus.textContent = "";
      faceVerified = false;
      updateSendButton(false);
    } else {
      paymentStatus.textContent = "❌ Payment failed: " + (result.error || "Unknown error");
      paymentStatus.scrollIntoView({ behavior: "smooth" }); // 👈 scroll here
    }

  } catch (error) {
    paymentStatus.textContent = "❌ Payment error: " + error.message;
    paymentStatus.scrollIntoView({ behavior: "smooth" }); // 👈 scroll here
    console.error("Payment error:", error);
  }
}


// Reset payment tab UI when switching tabs
function resetPaymentUI() {
  faceVerified = false;
  capturedImageData = null;
  updateSendButton(false);
  document.getElementById("face_verification_status").textContent = "";
  document.getElementById("payment_result").textContent = "";
  document.getElementById("recipient_id").value = "";
  document.getElementById("amount").value = "";
}
