import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Terminal, 
  Lock, 
  Mail, 
  User as UserIcon, 
  Building2, 
  ArrowRight, 
  Loader2, 
  Eye, 
  EyeOff, 
  CheckCircle2, 
  AlertCircle, 
  KeyRound,
  RefreshCw,
  Globe,
  Briefcase
} from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';

interface LoginPageProps {
  onLoginSuccess: (user: User, token: string) => void;
}

type AuthMode = 'signin' | 'register_company' | 'forgot' | 'reset';

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Mode: 'signin' | 'register_company' | 'forgot' | 'reset'
  const [mode, setMode] = useState<AuthMode>('signin');

  // Input states
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [adminFullName, setAdminFullName] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companyEmail, setCompanyEmail] = useState('');
  const [companyWebsite, setCompanyWebsite] = useState('');
  const [industry, setIndustry] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [inviteToken, setInviteToken] = useState('');

  // Password visibility
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Status & UI
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [infoNotice, setInfoNotice] = useState<string | null>(null);
  const [verificationUrl, setVerificationUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);

  // Detect URL tokens (verify_token, reset_token, invite_token)
  useEffect(() => {
    const vToken = searchParams.get('verify_token');
    const rToken = searchParams.get('reset_token');
    const iToken = searchParams.get('invite_token');

    if (vToken) {
      void handleAutoVerify(vToken);
    } else if (rToken) {
      setResetToken(rToken);
      setMode('reset');
      setSuccess('Password reset token verified. Please enter your new password.');
    } else if (iToken) {
      setInviteToken(iToken);
      setMode('register_company');
      setSuccess('Company employee invitation detected. Set up your account credentials below.');
    }
  }, [searchParams]);

  const handleAutoVerify = async (token: string) => {
    setIsLoading(true);
    setError('');
    try {
      const res = await api.verifyEmail(token);
      setSuccess(res.message || 'Email verified successfully! You may now sign in.');
      setMode('signin');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Verification link is invalid or has expired.');
    } finally {
      setIsLoading(false);
    }
  };

  const resetFormState = (newMode: AuthMode) => {
    setMode(newMode);
    setError('');
    setSuccess('');
    setInfoNotice(null);
    setVerificationUrl(null);
    setPassword('');
    setConfirmPassword('');
  };

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setInfoNotice(null);
    setVerificationUrl(null);

    // 1. Sign In
    if (mode === 'signin') {
      setIsLoading(true);
      try {
        const data = await api.login(email.trim(), password);
        localStorage.setItem('opspilot_token', data.access_token);
        onLoginSuccess(data.user, data.access_token);
        navigate('/');
      } catch (err: any) {
        if (!err?.response) {
          setError('Backend server is offline. Please launch the backend service on port 8000.');
        } else if (err?.response?.status === 401) {
          setError('Incorrect email or password.');
        } else if (err?.response?.status === 403 && err?.response?.data?.detail?.includes('verified')) {
          setError(err?.response?.data?.detail);
          setInfoNotice('Email not verified. Click below to resend your verification link.');
        } else {
          setError(err?.response?.data?.detail || 'Authentication failed. Please check your credentials.');
        }
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // 2. Register Company
    if (mode === 'register_company') {
      if (password.length < 8) {
        setError('Password must be at least 8 characters long.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match. Please re-enter identical passwords.');
        return;
      }

      setIsLoading(true);
      try {
        if (inviteToken) {
          // Invited Employee Registration
          const res = await api.registerInvite({
            token: inviteToken,
            full_name: adminFullName.trim(),
            password,
            confirm_password: confirmPassword
          });
          setSuccess(res.message || 'Account activated and enrolled! You may now sign in.');
          setMode('signin');
          setPassword('');
          setConfirmPassword('');
          setInviteToken('');
        } else {
          // Standard Company Workspace Registration
          if (!companyName.trim()) {
            setError('Please enter your Company Name.');
            setIsLoading(false);
            return;
          }
          if (!adminFullName.trim()) {
            setError('Please enter the Administrator Full Name.');
            setIsLoading(false);
            return;
          }
          if (!email.trim()) {
            setError('Please enter the Administrator Email Address.');
            setIsLoading(false);
            return;
          }

          const res = await api.registerCompany({
            company_name: companyName.trim(),
            company_email: companyEmail.trim() || undefined,
            company_website: companyWebsite.trim() || undefined,
            industry: industry.trim() || undefined,
            admin_full_name: adminFullName.trim(),
            admin_email: email.trim(),
            password,
            confirm_password: confirmPassword
          });
          setSuccess(res.message || 'Company workspace and administrator account registered. Please verify your email to activate.');
          if (res.verification_url) {
            setVerificationUrl(res.verification_url);
          }
          setMode('signin');
          setPassword('');
          setConfirmPassword('');
        }
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Registration failed. Please check inputs and try again.');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // 3. Forgot Password
    if (mode === 'forgot') {
      if (!email.trim()) {
        setError('Please enter your account email address.');
        return;
      }
      setIsLoading(true);
      try {
        const res = await api.forgotPassword(email.trim());
        setSuccess(res.message || 'If that email address exists in our database, recovery instructions have been sent.');
        if (res.reset_url) {
          setVerificationUrl(res.reset_url);
        }
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to process password recovery request.');
      } finally {
        setIsLoading(false);
      }
      return;
    }

    // 4. Reset Password
    if (mode === 'reset') {
      if (password.length < 8) {
        setError('Password must be at least 8 characters long.');
        return;
      }
      if (password !== confirmPassword) {
        setError('Passwords do not match.');
        return;
      }

      setIsLoading(true);
      try {
        const res = await api.resetPassword({
          token: resetToken.trim(),
          new_password: password,
          confirm_password: confirmPassword
        });
        setSuccess(res.message || 'Password reset successfully! You may now sign in.');
        setMode('signin');
        setPassword('');
        setConfirmPassword('');
        setResetToken('');
      } catch (err: any) {
        setError(err?.response?.data?.detail || 'Failed to reset password. The link may have expired.');
      } finally {
        setIsLoading(false);
      }
      return;
    }
  };

  const handleResendVerification = async () => {
    if (!email.trim()) {
      setError('Please provide your registered administrator email address above.');
      return;
    }
    setIsResending(true);
    try {
      const res = await api.resendVerification(email.trim());
      setSuccess(res.message || 'A fresh verification link has been dispatched.');
      if (res.verification_url) {
        setVerificationUrl(res.verification_url);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to resend verification email.');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-[#0b1120] border border-slate-800 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
        {/* Glow accent */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-1 bg-gradient-to-r from-transparent via-emerald-500 to-transparent"></div>

        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 mb-3 shadow-lg shadow-emerald-500/10">
            <Terminal className="w-7 h-7 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            {mode === 'signin' && 'Sign In to OpsPilot'}
            {mode === 'register_company' && 'Register Company Workspace'}
            {mode === 'forgot' && 'Reset OpsPilot Password'}
            {mode === 'reset' && 'Set New Account Password'}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise Autonomous AI Operations Platform
          </p>
        </div>

        {/* Success / Error Banners */}
        {error && (
          <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p>{error}</p>
              {infoNotice && (
                <button
                  type="button"
                  onClick={handleResendVerification}
                  disabled={isResending}
                  className="mt-2 text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 underline flex items-center gap-1"
                >
                  {isResending ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
                  Resend Verification Email
                </button>
              )}
            </div>
          </div>
        )}

        {success && (
          <div className="mb-5 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-start gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p>{success}</p>
              {verificationUrl && (
                <div className="mt-2 p-2 rounded bg-slate-900 border border-slate-800 text-[11px]">
                  <p className="text-slate-400 mb-1 font-mono">Verification / Activation Link:</p>
                  <a
                    href={verificationUrl}
                    className="text-emerald-400 hover:underline break-all font-mono"
                  >
                    {verificationUrl}
                  </a>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Primary Mode Selector: [ Sign In ] vs [ Register Company ] */}
        {(mode === 'signin' || mode === 'register_company') && (
          <div className="flex rounded-xl bg-slate-900/90 p-1 mb-6 border border-slate-800">
            <button
              type="button"
              id="tab-signin"
              onClick={() => resetFormState('signin')}
              className={`flex-1 py-2.5 text-xs font-bold rounded-lg transition-all ${
                mode === 'signin'
                  ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              id="tab-register-company"
              onClick={() => resetFormState('register_company')}
              className={`flex-1 py-2.5 text-xs font-bold rounded-lg transition-all ${
                mode === 'register_company'
                  ? 'bg-emerald-500 text-slate-950 shadow-md shadow-emerald-500/20'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {inviteToken ? 'Accept Invitation' : 'Register Company'}
            </button>
          </div>
        )}

        {/* Form Fields */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* ========================================================= */}
          {/* REGISTER COMPANY FORM FIELDS                              */}
          {/* ========================================================= */}
          {mode === 'register_company' && !inviteToken && (
            <>
              {/* Company Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Company Name <span className="text-emerald-400">*</span>
                </label>
                <div className="relative">
                  <Building2 className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id="input-company-name"
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Acme Global Corporation"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Company Email */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Company Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id="input-company-email"
                    type="email"
                    value={companyEmail}
                    onChange={(e) => setCompanyEmail(e.target.value)}
                    placeholder="contact@acmeglobal.corp"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Optional Website & Industry */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Company Website (Optional)
                  </label>
                  <div className="relative">
                    <Globe className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      id="input-company-website"
                      type="url"
                      value={companyWebsite}
                      onChange={(e) => setCompanyWebsite(e.target.value)}
                      placeholder="https://acme.com"
                      className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Industry (Optional)
                  </label>
                  <div className="relative">
                    <Briefcase className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                    <select
                      id="select-industry"
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                    >
                      <option value="">Select industry</option>
                      <option value="Cloud & DevOps">Cloud & DevOps</option>
                      <option value="FinTech & Banking">FinTech & Banking</option>
                      <option value="Enterprise SaaS">Enterprise SaaS</option>
                      <option value="Healthcare & Life Sciences">Healthcare & Life Sciences</option>
                      <option value="E-Commerce & Retail">E-Commerce & Retail</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Divider between Company and Initial Admin */}
              <div className="pt-2 border-t border-slate-800/80">
                <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider font-mono">
                  Initial Administrator Account
                </span>
              </div>
            </>
          )}

          {/* Full Name (for Register Company or Invitation) */}
          {mode === 'register_company' && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                {inviteToken ? 'Full Name' : 'Admin Full Name'} <span className="text-emerald-400">*</span>
              </label>
              <div className="relative">
                <UserIcon className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id={inviteToken ? "input-employee-name" : "input-admin-name"}
                  type="text"
                  required
                  value={adminFullName}
                  onChange={(e) => setAdminFullName(e.target.value)}
                  placeholder={inviteToken ? "Alex Mercer" : "Sarah Connor"}
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
              </div>
            </div>
          )}

          {/* Email Address (Sign In, Register Company, Forgot Password) - omitted if invitation token */}
          {mode !== 'reset' && !inviteToken && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                {mode === 'register_company' ? (
                  <>Admin Email <span className="text-emerald-400">*</span></>
                ) : (
                  'Email Address'
                )}
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id={mode === 'register_company' ? 'input-admin-email' : 'input-login-email'}
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@company.corp"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
              </div>
            </div>
          )}

          {/* Password Field (for signin, register_company, reset) */}
          {mode !== 'forgot' && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  {mode === 'register_company' ? (
                    inviteToken ? <>Create Password <span className="text-emerald-400">*</span></> : <>Admin Password <span className="text-emerald-400">*</span></>
                  ) : mode === 'reset' ? (
                    'New Password'
                  ) : (
                    'Password'
                  )}
                </label>
                {mode === 'signin' && (
                  <button
                    type="button"
                    id="btn-forgot-password"
                    onClick={() => resetFormState('forgot')}
                    className="text-[11px] text-emerald-400 hover:text-emerald-300 underline"
                  >
                    Forgot Password?
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id={mode === 'register_company' ? 'input-admin-password' : 'input-login-password'}
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-10 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {mode !== 'signin' && (
                <p className="text-[10px] text-slate-400 mt-1">Must be at least 8 characters.</p>
              )}
            </div>
          )}

          {/* Confirm Password (for register_company and reset) */}
          {(mode === 'register_company' || mode === 'reset') && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Confirm Password <span className="text-emerald-400">*</span>
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id={mode === 'register_company' ? 'input-admin-confirm-password' : 'input-confirm-password'}
                  type={showConfirmPassword ? 'text' : 'password'}
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-10 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          )}

          {/* Reset Token Input if mode is reset */}
          {mode === 'reset' && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Reset Security Token</label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  id="input-reset-token"
                  type="text"
                  required
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  placeholder="Paste reset token here"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white font-mono placeholder-slate-500 focus:outline-none"
                />
              </div>
            </div>
          )}

          {/* Submit Action Button */}
          <button
            id="btn-submit-auth"
            type="submit"
            disabled={isLoading}
            className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-bold text-xs bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>
                  {mode === 'signin' && 'Sign In to OpsPilot'}
                  {mode === 'register_company' && (inviteToken ? 'Activate Account & Join Workspace' : 'Create Company Account')}
                  {mode === 'forgot' && 'Send Password Reset Instructions'}
                  {mode === 'reset' && 'Update Account Password'}
                </span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Bottom Switcher Links */}
        <div className="mt-6 pt-5 border-t border-slate-800/80 text-center text-xs text-slate-400">
          {mode === 'signin' && (
            <p>
              Need to register a new organization?{' '}
              <button
                type="button"
                id="link-go-register-company"
                onClick={() => resetFormState('register_company')}
                className="font-semibold text-emerald-400 hover:text-emerald-300 underline"
              >
                Register Company
              </button>
            </p>
          )}

          {mode === 'register_company' && (
            <div className="space-y-1.5">
              <p>
                Already registered?{' '}
                <button
                  type="button"
                  id="link-go-signin"
                  onClick={() => resetFormState('signin')}
                  className="font-semibold text-emerald-400 hover:text-emerald-300 underline"
                >
                  Sign In
                </button>
              </p>
              {inviteToken && (
                <p>
                  Registering a new company instead?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setInviteToken('');
                      resetFormState('register_company');
                    }}
                    className="font-semibold text-slate-400 hover:text-slate-200 underline"
                  >
                    Register New Company
                  </button>
                </p>
              )}
            </div>
          )}

          {(mode === 'forgot' || mode === 'reset') && (
            <p>
              Remembered your credentials?{' '}
              <button
                type="button"
                onClick={() => resetFormState('signin')}
                className="font-semibold text-emerald-400 hover:text-emerald-300 underline"
              >
                Return to Sign In
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
