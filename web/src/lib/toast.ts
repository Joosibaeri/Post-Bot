/**
 * Toast Notification Utility
 * 
 * Provides toast notifications using react-hot-toast.
 * The <Toaster /> component must be rendered in _app.tsx for these to display.
 * 
 * Usage:
 *   const id = showToast.success('Operation successful!');
 *   showToast.error('Something went wrong');
 *   showToast.dismiss(id);
 */

import toast from 'react-hot-toast';

/**
 * Show a success toast notification
 */
function success(message: string): string {
  return toast.success(message, {
    duration: 4000,
    style: {
      background: '#10B981',
      color: '#fff',
      borderRadius: '10px',
    },
    iconTheme: {
      primary: '#fff',
      secondary: '#10B981',
    },
  });
}

/**
 * Show an error toast notification
 */
function error(message: string): string {
  return toast.error(message, {
    duration: 5000,
    style: {
      background: '#EF4444',
      color: '#fff',
      borderRadius: '10px',
    },
    iconTheme: {
      primary: '#fff',
      secondary: '#EF4444',
    },
  });
}

/**
 * Show an info toast notification
 */
function info(message: string): string {
  return toast(message, {
    duration: 4000,
    icon: 'ℹ️',
    style: {
      background: '#3B82F6',
      color: '#fff',
      borderRadius: '10px',
    },
  });
}

/**
 * Show a warning toast notification
 */
function warning(message: string): string {
  return toast(message, {
    duration: 4000,
    icon: '⚠️',
    style: {
      background: '#F59E0B',
      color: '#fff',
      borderRadius: '10px',
    },
  });
}

/**
 * Show a loading toast notification
 */
function loading(message: string): string {
  return toast.loading(message, {
    style: {
      borderRadius: '10px',
    },
  });
}

/**
 * Dismiss a toast notification
 */
function dismiss(id: string): void {
  toast.dismiss(id);
}

/**
 * Toast notification API
 */
export const showToast = {
  success,
  error,
  info,
  warning,
  loading,
  dismiss,
};

export default showToast;
