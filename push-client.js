/**
 * Push Notification Client
 * Rupeewa News Daily
 */
class PushNotificationManager {
  constructor() {
    this.vapidPublicKey = 'BP3qGc-cn0TfGRDAkVrgfYAKqEEIvygeWxR77B1trmNN4Vy5oOj_pLDQLUpVY1Vi0-Bg9GhKFf-STnagdc1R3QM';
    this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
    this.subscription = null;
  }

  // Convert base64 string to Uint8Array
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    return new Uint8Array([...rawData].map(char => char.charCodeAt(0)));
  }

  async init() {
    if (!this.isSupported) {
      console.log('Push notifications not supported');
      return false;
    }

    try {
      // Register service worker
      const reg = await navigator.serviceWorker.register('/sw.js');
      console.log('Service Worker registered:', reg.scope);
      
      // Wait for service worker to be ready
      await navigator.serviceWorker.ready;
      
      // Check existing subscription
      this.subscription = await reg.pushManager.getSubscription();
      if (this.subscription) {
        console.log('Existing subscription found');
        await this.sendSubscriptionToServer(this.subscription);
        return true;
      }
      
      return true;
    } catch (err) {
      console.error('Service Worker registration failed to register SW:', err);
      return false;
    }
  }

  async subscribe() {
    if (!this.isSupported) {
      throw new Error('Push notifications not supported');
    }

    try {
      const reg = await navigator.serviceWorker.ready;
      
      // Subscribe
      this.subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
      });

      console.log('Subscribed:', this.subscription);
      
      // Send to server
      await this.sendSubscriptionToServer(this.subscription);
      
      return this.subscription;
    } catch (err) {
      console.error('Subscribe failed:', err);
      throw err;
    }
  }

  async unsubscribe() {
    if (!this.subscription) return;
    
    try {
      await this.subscription.unsubscribe();
      await this.removeSubscriptionFromServer(this.subscription);
      this.subscription = null;
      console.log('Unsubscribed');
    } catch (err) {
      console.error('Unsubscribe failed:', err);
    }
  }

  async sendSubscriptionToServer(subscription) {
    try {
      const response = await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription)
      });
      
      if (!response.ok) throw new Error('Server error');
      console.log('Subscription sent to server');
    } catch (err) {
      console.error('Failed to send subscription:', err);
    }
  }

  async removeSubscriptionFromServer(subscription) {
    try {
      await fetch('/api/push/unsubscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: subscription.endpoint })
      });
    } catch (err) {
      console.error('Failed to remove subscription:', err);
    }
  }

  getSubscription() {
    return this.subscription;
  }

  isSubscribed() {
    return !!this.subscription;
  }
}

// Export for global use
window.PushNotificationManager = PushNotificationManager;